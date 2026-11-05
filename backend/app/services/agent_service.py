from asyncio.log import logger
import os 
from typing import Any

from sqlalchemy.orm import Session
from app.models.user import User
from app.services import agent_tools
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState,START,END,StateGraph
from langchain_core.messages import AIMessage,HumanMessage,SystemMessage,ToolMessage
from langgraph.prebuilt import ToolNode,tools_condition
from langgraph.types import interrupt,Command
from app.schemes.ai import chatRequest
from app.common.exceptions import BusinessException

from app.config import settings,BASE_DIR

from collections.abc import AsyncIterator
import uuid
from app.branding import PRODUCT_NAME
from app.access import user_checkpoint_config

SYSTEM_PROMPT = "你是" + PRODUCT_NAME + """，回答要简洁
你可以:
1.使用search_kb 查询实验室的预约规则，安全，开放时间，设备使用等问题
2.使用search_open_labs/search_labs_equipment 查询真实的实验室以及设备
3.在用户进行预约确认之后，使用create_lab_reservation 来进行真实的预约落库
4.使用get_today 来进行日期的换算

必须遵守：当用户提到了 今天、明天、后天 等日期相关的问题，请先调用 get_today 来获取当前日期，**不要直接返回 我需要确定明天的具体日期**。

在提交预约之前，需要向用户复述：实验室ID和名称（或设备ID和名称）、日期、开始时间、结束时间。并得到用户的确认再进行下一步操作。
在用户说【确认】【确认预约】【就这样】【可以】等确认性回复之前，不要调用create_lab_reservation。
工作流的确认环节里如果缺少了lab_id,请先 search_open_labs 查到了lab_id 再创建,不要瞎写。
工作流的确认环节中如果缺少了equipment_id，请先 search_labs_equipment 查到了具体的lab_id以及equipment_id之后再创建，不要瞎写

预约成功之后状态是待审核，必须管理员确认后实验室（或设备）才能使用
不要瞎编数据库里没有的实验室或者设备信息
如果是问开放时间或者实验室规则，优先调用 search_kb ，不要凭空回复

"""
TOOL_LABLES = {
    "search_kb":"检索实验室知识库",
    "search_open_labs":"查询开放实验室",
    "search_labs_equipment":"查询实验室设备",
    "create_lab_reservation":"提交预约",
    "get_today":"获取今天的日期"
}

#写工具名：只有它会真正落库，必须在执行前强制确认
RESERVE_TOOL = "create_lab_reservation"

CHECKPOINT_DB = BASE_DIR / "data" / "checkpoints.sqlite"
#图里节点是 async def，只能用 AsyncSqliteSaver；实例在 lifespan 里创建
ASYNC_CHECKPOINTER = None

def new_thread_id() ->str:
    return uuid.uuid4().hex

def _config(thread_id:str) ->dict:
    """langgraph 靠 configurable.thread_id 定位这条会话的 checkpoint 分支"""
    return {"configurable":{"thread_id":thread_id},"recursion_limit":10}

def _chunk_text(chunk:Any) ->str :
    """从模型流式抠出纯文本。
    content 有时是[{type,text},...] 这种块列表，要统一成字符串。
    """
    if chunk is None:
        return ""

    content = getattr(chunk,"content",None)
    if isinstance(content,list):
        parts = []
        for part in content:
            if isinstance(part,dict):
                parts.append(part.get("text",""))
            elif isinstance(part,str):
                parts.append(part)
        return "".join(parts)
    return str(content) if content is not None else ""
    

def _build_history (data:chatRequest):
    """前端只传 user/assistant 文本，转成 LangChain 消息对象。"""
    history = []
    for message in data.messages:
        if message.role =='user' and message.content.strip():
            history.append(HumanMessage(content = message.content.strip()))
        elif message.role =='assistant' and message.content.strip():
            history.append(AIMessage(content=message.content.strip()))
    if not history:
        raise BusinessException("请输入您要对话的内容")
    return history


def _tool_output_preview(output:Any,limit:int = 200) ->str:
    """把工具调用收成短预览，避免整段 JSON 刷到前端过程区"""
    #langGraph 里工具结果经常是ToolMessage，正文在.content
    if isinstance(output ,ToolMessage):
        output = output.content
    text = output if isinstance(output,str) else str(output)
    #太长就截断，末尾加省略号
    return text if len(text) <= limit else text[:limit]

async def stream_agent(db:Session,user:User,data:chatRequest,thread_id:str|None = None)->AsyncIterator[dict]:
    """
    AsyncIterator生成器，边跑agent边yield事件，供sse推给前端。
    事件类型：thread / status / tool_start / tool_end / token / interrupt / done / error
    """
    thread_id = thread_id or new_thread_id()
    config = user_checkpoint_config(thread_id, user.id)
    try :
        history = _build_history(data)
        agent = build_agent(db=db,current_user=user,use_mcp=True)
        # *history把列表拆开，和systemMessage 拼成完整的messages
        inputs = {"messages":[SystemMessage(content=SYSTEM_PROMPT),*history]}

        #先把会话id交出去，恢复中断时前端要带回来
        yield {"type":"thread","thread_id":thread_id}
        #yield 先交出这一条，生成器暂停，调用方再次取值时继续执行
        yield {"type":"status","message":"正在思考..."}

        #astream_events:图每走一步（调用工具，吐字）都会冒出一个内部时间
        async for event in agent.astream_events(
            inputs,
            version="v2",
            config=config
        ):
            kind = event.get("event")
            if kind == "on_tool_start":
                name = event.get("name") or ""
                yield {
                    "type":"tool_start",
                    "name":name,
                    "label":TOOL_LABLES.get(name,name),
                }
            elif kind == "on_tool_end":
                name = event.get("name") or ""
                yield {
                    "type":"tool_end",
                    "name":name,
                    "label":TOOL_LABLES.get(name,name),
                    "preview":_tool_output_preview(
                        (event.get("data")or {}).get("output")
                    ),
                }
            elif kind =="on_chat_model_stream":
                #只收agent 节点的字;其他内部的噪声丢掉
                meta = event.get("metadata")or {}
                if meta.get("langgraph_node") not in (None,"agent"):
                    continue
                text = _chunk_text((event.get("data") or {}).get("chunk"))
                if text:
                    yield {"type":"token","content":text}

        #图停在confirm节点等确认时，checkpoint里会留下pending interrupt
        pending = _pending_interrupt(await agent.aget_state(config))
        if pending is None:
            #正常跑完，不要在done里再带一份全文，前端已经用token拼好了
            yield {"type":"done"}
        else:
            yield {
                "type":"interrupt",
                "thread_id":thread_id,
                "action":RESERVE_TOOL,
                "payload":pending,
            }


    except BusinessException as e :
        yield {"type":"error","message":e.message}
    except Exception:
        logger.exception("stream_agent failed")
        yield {"type":"error","message":"大模型调用失败。请稍后重试"}



def _reserve_call(message:Any) ->dict:
    """从AIMessage的tool_calls里挑出写工具那一项，没有则返回空dict"""
    for call in getattr(message,"tool_calls",None) or ():
        if call.get("name") == RESERVE_TOOL:
            return call
    return {}

def _route_after_agent(state:MessagesState) ->str:
    """没工具调用就结束；有写工具先过confirm，其余直接进tools"""
    last = state["messages"][-1]
    if not getattr(last,"tool_calls",None):
        return END
    return "confirm" if _reserve_call(last) else "tools"

def _route_after_confirm(state:MessagesState) ->str:
    """confirm拒绝时会补一条ToolMessage，直接回agent；同意则原样进tools"""
    return "agent" if isinstance(state["messages"][-1],ToolMessage) else "tools"

def _pending_interrupt(snapshot:Any) ->dict|None:
    """从暂停的图状态里取出 interrupt() 的 payload，没有则返回None"""
    for task in getattr(snapshot,"tasks",None) or ():
        for item in getattr(task,"interrupts",None) or ():
            return item.value
    return None

def _last_ai_text(result:dict) ->str:
    """取最后一条有正文的AIMessage；工具轮次的空content跳过"""
    messages = result.get("messages") or []
    for message in reversed(messages):
        if isinstance(message,AIMessage):
            content = _chunk_text(message).strip()
            if content:
                return content
    raise BusinessException(message="大模型没有返回响应")

def build_agent(db:Session,current_user:User,use_mcp:bool=False):
    tools = agent_tools.build_tool(db,current_user=current_user)
    if use_mcp:
        #只读查询走 MCP；写工具 create_lab_reservation 保留在本地，由 confirm 节点强制确认
        from app.services.mcp_client import mcp_client
        if mcp_client.tools:
            names = {tool.name for tool in mcp_client.tools}
            tools = [tool for tool in tools if tool.name not in names] + mcp_client.tools
    llm = ChatOpenAI(
        model = settings.LLM_MODEL,
        base_url = settings.LLM_BASE_URL,
        api_key= settings.SILICONFLOW_API_KEY,
        temperature=0,
        streaming=True
    ).bind_tools(tools)

    async def agent_node(state:MessagesState):
        """langGraph执行的工作流节点"""
        response = await llm.ainvoke(state["messages"])
        return {"messages":[response]}

    def confirm_node(state:MessagesState):
        """写工具落库前的硬确认：图在这里挂起，等 /ai/chat/resume 带 approved 回来"""
        call = _reserve_call(state["messages"][-1])
        decision = interrupt({
            "tool":RESERVE_TOOL,
            "tool_call_id":call.get("id"),
            "args":call.get("args") or {},
            "question":"是否确认提交这次预约？确认后才会写库。",
        })
        approved = decision.get("approved") if isinstance(decision,dict) else bool(decision)
        if approved:
            return {}
        #拒绝时补一条ToolMessage：让模型知道这次没执行，而不是自己编一个结果
        return {"messages":[ToolMessage(
            content="用户取消了本次预约，未执行任何写库操作。",
            tool_call_id=call.get("id")
        )]}

    graph = StateGraph(MessagesState)
    graph.add_node("agent",agent_node)
    graph.add_node("confirm",confirm_node)
    graph.add_node("tools",ToolNode(tools))
    graph.add_edge(START,"agent")
    graph.add_conditional_edges(
       "agent",_route_after_agent,{"confirm":"confirm","tools":"tools",END:END}
    )
    graph.add_conditional_edges(
       "confirm",_route_after_confirm,{"tools":"tools","agent":"agent"}
    )
    graph.add_edge("tools","agent")
    return graph.compile(checkpointer=ASYNC_CHECKPOINTER)


async def run_agent(db:Session,current_user:User,data:chatRequest,thread_id:str|None = None) -> str:
    """非流式的整段问答（POST /ai/chat 用）。执行链路与 stream_agent 相同，只是不推事件。"""
    thread_id = thread_id or data.thread_id or new_thread_id()
    config = user_checkpoint_config(thread_id, current_user.id)
    history = _build_history(data)
    agent = build_agent(db=db,current_user=current_user)
    try:
        result = await agent.ainvoke(
            {"messages":[SystemMessage(content=SYSTEM_PROMPT),*history]},
            config=config
        )
    except BusinessException:
        raise
    except Exception:
        logger.exception("run_agent failed")
        raise BusinessException(message="大模型调用失败，请稍后重试")

    #非流式接口拿到的是"需要确认"，不能当成没回答
    if _pending_interrupt(await agent.aget_state(config)) is not None:
        raise BusinessException(
            message="预约信息已准备好，请在对话中核对并确认后提交。"
        )
    return _last_ai_text(result)


async def resume_agent(db:Session,current_user:User,thread_id:str,approved:bool) ->str:
    """带着人工确认结果恢复被中断的图：同意则真正执行写工具，拒绝则回agent说明取消"""
    agent = build_agent(db=db,current_user=current_user)
    try:
        config = user_checkpoint_config(thread_id, current_user.id)
        if _pending_interrupt(await agent.aget_state(config)) is None:
            raise BusinessException(message="没有待确认的操作，请重新发起咨询", code=409)
        result = await agent.ainvoke(
            Command(resume={"approved":bool(approved)}),
            config=config
        )
    except BusinessException:
        raise
    except Exception:
        logger.exception("resume_agent failed")
        raise BusinessException(message="恢复会话失败，请重新发起咨询")
    return _last_ai_text(result)
