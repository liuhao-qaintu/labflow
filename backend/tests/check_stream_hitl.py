"""流式 HITL + 异步 checkpointer 自检。

验证异步事件流与状态恢复的配合：
  astream_events（异步）必须配 AsyncSqliteSaver，resume 也必须走 ainvoke。
不调真实模型；写工具用替身统计调用次数。
"""
import asyncio
import sys
import tempfile
import uuid
from contextlib import AsyncExitStack
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.services import agent_service

CALLS = {"reserve": 0}


@tool
def create_lab_reservation(lab_id: int, date: str, start_time: str, end_time: str) -> str:
    """创建预约单预约实验室或设备"""
    CALLS["reserve"] += 1
    return '{"结果":true,"message":"预约已提交，请等待管理员审核"}'


class FakeLLM:
    def __init__(self, **kwargs):
        pass

    def bind_tools(self, tools):
        return self

    async def ainvoke(self, messages):
        if isinstance(messages[-1], ToolMessage):
            return AIMessage(content="已按您的确认提交申请。")
        return AIMessage(
            content="",
            tool_calls=[{
                "name": "create_lab_reservation",
                "args": {"lab_id": 1, "date": "2026-11-01",
                         "start_time": "09:00", "end_time": "10:00"},
                "id": "call_reserve_1",
            }],
        )


async def stream_once(agent, cfg, text="帮我约明天 9 点的 1 号实验室"):
    async for _ in agent.astream_events(
        {"messages": [SystemMessage(content="test"), HumanMessage(content=text)]},
        version="v2",
        config=cfg,
    ):
        pass


async def main():
    ok = True
    demo_user = SimpleNamespace(id=1)
    tmp = Path(tempfile.gettempdir()) / f"lab_cp_{uuid.uuid4().hex}.sqlite"
    stack = AsyncExitStack()
    saver = await stack.enter_async_context(AsyncSqliteSaver.from_conn_string(str(tmp)))
    await saver.setup()

    agent_service.ASYNC_CHECKPOINTER = saver
    agent_service.agent_tools.build_tool = lambda db, current_user: [create_lab_reservation]
    agent_service.ChatOpenAI = FakeLLM

    # 1. 流式跑到中断：不得执行写工具
    agent = agent_service.build_agent(db=None, current_user=None)
    cfg = agent_service.user_checkpoint_config("t-approve", demo_user.id)
    await stream_once(agent, cfg)
    pending = agent_service._pending_interrupt(await agent.aget_state(cfg))
    ok &= pending is not None and CALLS["reserve"] == 0
    print(f"[1] 流式中断且未写库: {'PASS' if pending is not None and CALLS['reserve'] == 0 else 'FAIL'}")

    # 2. 异步 resume(approved=True)：真正执行
    text = await agent_service.resume_agent(db=None, current_user=demo_user, thread_id="t-approve", approved=True)
    ok &= CALLS["reserve"] == 1
    print(f"[2] 异步恢复后写库: {'PASS' if CALLS['reserve'] == 1 else 'FAIL'}（次数={CALLS['reserve']}），回复={text!r}")

    # 3. 拒绝：不得执行
    CALLS["reserve"] = 0
    agent2 = agent_service.build_agent(db=None, current_user=None)
    cfg2 = agent_service.user_checkpoint_config("t-reject", demo_user.id)
    await stream_once(agent2, cfg2)
    await agent_service.resume_agent(db=None, current_user=demo_user, thread_id="t-reject", approved=False)
    ok &= CALLS["reserve"] == 0
    print(f"[3] 拒绝后未写库: {'PASS' if CALLS['reserve'] == 0 else 'FAIL'}（次数={CALLS['reserve']}）")

    await stack.aclose()
    tmp.unlink(missing_ok=True)
    print("\nRESULT:", "ALL PASS" if ok else "FAILED")
    return ok


if __name__ == "__main__":
    sys.exit(0 if asyncio.run(main()) else 1)
