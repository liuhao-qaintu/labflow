"""把 MCP Server 暴露的工具接成 LangChain 工具（stdio 传输）。

Agent 启动时拉起 app.mcp_server 子进程，走 MCP 的 initialize / tools/list / tools/call；
接口失败不影响主流程，调用方会回退到本地原生工具。
"""
import sys
from contextlib import AsyncExitStack

from langchain_core.tools import StructuredTool
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from pydantic import create_model

from app.config import BASE_DIR,settings

_TYPE_MAP = {"integer": int, "number": float, "boolean": bool, "array": list, "object": dict}


def _args_model(tool_name, schema):
    """把 MCP 的 inputSchema 转成 LangChain 需要的 pydantic 参数模型。"""
    fields = {}
    required = set(schema.get("required") or [])
    for key, spec in (schema.get("properties") or {}).items():
        py_type = _TYPE_MAP.get(spec.get("type"), str)
        default = ... if key in required else spec.get("default", None)
        fields[key] = (py_type, default)
    return create_model(f"{tool_name}_args", **fields)


class LabMCPClient:
    def __init__(self):
        self._stack = None
        self._session = None
        self.tools = []

    async def start(self):
        stack = AsyncExitStack()
        try:
            params = StdioServerParameters(
                command=sys.executable,
                args=["-m", "app.mcp_server"],
                cwd=str(BASE_DIR),
                env={
                    "DATABASE_URL":settings.DATABASE_URL,
                    "JWT_SECRET_KEY":settings.JWT_SECRET_KEY,
                    "LLM_BASE_URL":settings.LLM_BASE_URL,
                    "LLM_MODEL":settings.LLM_MODEL,
                    "PYTHONDONTWRITEBYTECODE":"1",
                },
            )
            read, write = await stack.enter_async_context(stdio_client(params))
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            listed = await session.list_tools()
        except Exception:
            await stack.aclose()
            raise
        self._stack, self._session = stack, session
        self.tools = [self._wrap(tool) for tool in listed.tools]
        return self.tools

    def _wrap(self, tool):
        async def call(**kwargs):
            result = await self._session.call_tool(tool.name, kwargs)
            texts = [item.text for item in result.content if getattr(item, "type", "") == "text"]
            return "\n".join(texts) or "（工具没有返回文本）"

        return StructuredTool(
            name=tool.name,
            description=tool.description or tool.name,
            args_schema=_args_model(tool.name, tool.input_schema or {}),
            coroutine=call,
        )

    async def stop(self):
        if self._stack is not None:
            await self._stack.aclose()
        self._stack = self._session = None
        self.tools = []


mcp_client = LabMCPClient()
