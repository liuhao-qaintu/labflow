"""MCP 链路自检：stdio 启动 → tools/list → 工具调用 → Agent 内实际调用。

需要 MySQL 运行；不调真实模型（用 FakeLLM 触发一次 get_today 工具调用）。
用法（在项目根目录）：
    .\\.venv\\Scripts\\python.exe backend\\tests\\check_mcp.py
"""
import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver

from app.services import agent_service
from app.services.mcp_client import mcp_client


class FakeLLM:
    """第一次调用就请求 get_today；拿到工具结果后收尾。"""

    def __init__(self, **kwargs):
        pass

    def bind_tools(self, tools):
        return self

    async def ainvoke(self, messages):
        if isinstance(messages[-1], ToolMessage):
            return AIMessage(content=f"工具返回：{messages[-1].content}")
        return AIMessage(
            content="",
            tool_calls=[{"name": "get_today", "args": {}, "id": "call_today_1"}],
        )


async def main():
    ok = True
    tools = await mcp_client.start()
    names = [tool.name for tool in tools]
    print(f"[1] tools/list: {names}")
    ok &= {"get_today", "search_open_labs", "search_labs_equipment"}.issubset(set(names))

    by_name = {tool.name: tool for tool in tools}
    today = await by_name["get_today"].ainvoke({})
    expected = datetime.now().strftime("%Y-%m-%d")
    print(f"[2] get_today: {today!r} (expect {expected})")
    ok &= today.strip() == expected

    labs = await by_name["search_open_labs"].ainvoke({"keywords": ""})
    print(f"[3] search_open_labs: {labs[:120]}...")
    ok &= '"labs"' in labs

    # Agent 内真实执行：只保留 MCP 工具，确认 ToolNode 能调用它
    agent_service.agent_tools.build_tool = lambda db, current_user: []
    agent_service.ChatOpenAI = FakeLLM
    agent_service.ASYNC_CHECKPOINTER = MemorySaver()
    agent = agent_service.build_agent(db=None, current_user=None, use_mcp=True)
    result = await agent.ainvoke(
        {"messages": [HumanMessage(content="今天几号")]},
        config=agent_service._config("mcp-test"),
    )
    tool_msgs = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    ran = bool(tool_msgs) and expected in tool_msgs[0].content
    print(f"[4] Agent 调用 MCP 工具: {'PASS' if ran else 'FAIL'} -> {tool_msgs[0].content if tool_msgs else '无工具结果'}")
    ok &= ran

    await mcp_client.stop()
    print("\nRESULT:", "ALL PASS" if ok else "FAILED")
    return ok


if __name__ == "__main__":
    sys.exit(0 if asyncio.run(main()) else 1)
