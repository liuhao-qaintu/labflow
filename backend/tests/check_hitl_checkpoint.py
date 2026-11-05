"""HITL + checkpoint 链路自检（不调真实模型、不连数据库、不写业务库）。

用法：在项目根目录下
    .\\.venv\\Scripts\\python.exe backend\\tests\\check_hitl_checkpoint.py

验证三件事：
1. 模型要调 create_lab_reservation 时，图停在 confirm 节点，工具没执行；
2. 同一个 thread_id 带 approved=True 恢复，工具才真正执行；
3. approved=False 恢复，工具不执行，并回一条"已取消"的 ToolMessage 给模型。
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from app.services import agent_service

CALLS = {"reserve": 0}


@tool
def create_lab_reservation(lab_id: int, date: str, start_time: str, end_time: str) -> str:
    """创建预约单预约实验室或设备"""
    CALLS["reserve"] += 1
    return '{"结果":true,"message":"预约已提交，请等待管理员审核"}'


class FakeLLM:
    """第一次调用就发起写工具调用；拿到工具结果后收尾成一句话。"""

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
                "args": {"lab_id": 1, "date": "2026-10-30",
                         "start_time": "09:00", "end_time": "10:00"},
                "id": "call_reserve_1",
            }],
        )


def _patch():
    agent_service.agent_tools.build_tool = lambda db, current_user: [create_lab_reservation]
    agent_service.ChatOpenAI = FakeLLM
    agent_service.ASYNC_CHECKPOINTER = MemorySaver()


def _inputs():
    return {"messages": [SystemMessage(content="test"), HumanMessage(content="帮我约明天 9 点的 1 号实验室")]}


async def _run():
    _patch()
    ok = True

    # ---- 1. 中断：工具不得执行 ----
    agent = agent_service.build_agent(db=None, current_user=None)
    cfg = agent_service._config("thread-approve")
    await agent.ainvoke(_inputs(), config=cfg)
    pending = agent_service._pending_interrupt(agent.get_state(cfg))
    stopped = pending is not None
    ok &= stopped and CALLS["reserve"] == 0
    print(f"[1] 中断且未执行工具: {'PASS' if stopped and CALLS['reserve'] == 0 else 'FAIL'}")
    if pending:
        print(f"    interrupt payload = {pending}")

    # ---- 2. 确认后恢复：工具必须执行 ----
    result = await agent.ainvoke(Command(resume={"approved": True}), config=cfg)
    ran = CALLS["reserve"] == 1
    tail = agent_service._last_ai_text(result)
    ok &= ran and tail == "已按您的确认提交申请。"
    print(f"[2] 确认后执行工具: {'PASS' if ran else 'FAIL'}（调用次数={CALLS['reserve']}），最终回复={tail!r}")

    # ---- 3. 拒绝后恢复：工具不得执行，且要回 ToolMessage ----
    CALLS["reserve"] = 0
    agent2 = agent_service.build_agent(db=None, current_user=None)
    cfg2 = agent_service._config("thread-reject")
    await agent2.ainvoke(_inputs(), config=cfg2)
    result2 = await agent2.ainvoke(Command(resume={"approved": False}), config=cfg2)
    msgs = result2["messages"]
    rejected_tool = [m for m in msgs if isinstance(m, ToolMessage) and "取消" in m.content]
    ok &= CALLS["reserve"] == 0 and bool(rejected_tool)
    print(f"[3] 拒绝后未执行工具: {'PASS' if CALLS['reserve'] == 0 else 'FAIL'}（调用次数={CALLS['reserve']}），"
          f"取消消息={'有' if rejected_tool else '无'}")

    return ok


if __name__ == "__main__":
    passed = asyncio.run(_run())
    print("\nRESULT:", "ALL PASS" if passed else "FAILED")
    sys.exit(0 if passed else 1)
