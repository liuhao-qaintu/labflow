import asyncio
import json

from fastapi import APIRouter,Depends
from app.schemes.ai import chatRequest,chatMessage,chatSoure,chatResponse,kbSearchRequest,kbSearchResponse,resumeRequest
from app.models.user import User
from app.dependencies.auth import get_current_user, get_current_developer
from app.access import public_chat_event
from app.services import ai_service
from app.common.response import Response
from app.services import kb_service
from app.common.exceptions import BusinessException
from sqlalchemy.orm import Session
from app.dependencies.auth import get_db
from app.services import agent_tools,agent_service
from app.database import SessionLocal
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/ai",tags=["AI相关的API"])

def _sse_line(payload:dict):
    """拼一条 SSE帧，以空行结束。"""
    return f"data:{json.dumps(payload,ensure_ascii=False)}\n\n"

@router.post('/chat')
async def chat(data:chatRequest,user:User = Depends(get_current_user),db:Session = Depends(get_db)):
    content = await agent_service.run_agent(data=data,db=db,current_user=user,thread_id=data.thread_id)
    return Response.success(data=chatMessage(role="assistant",content = content))

@router.post('/chat/resume')
async def chat_resume(data:resumeRequest,user:User = Depends(get_current_user),db:Session = Depends(get_db)):
    """人工确认后恢复被 interrupt 挂起的图：approved=true 才真正执行预约写库"""
    content = await agent_service.resume_agent(
        db=db,current_user=user,thread_id=data.thread_id,approved=data.approved
    )
    return Response.success(data=chatMessage(role="assistant",content = content))

@router.post('/chat/stream')
async def chat_stream(data: chatRequest,user:User=Depends(get_current_user)):
    user_id = user.id

    async def event_gen():
        with SessionLocal() as db :
            #db.get 是同步 pymysql 查询，直接调会卡住事件循环（所有 SSE 一起卡），丢线程池
            stream_user = await asyncio.to_thread(db.get,User,user_id)
            #鉴权完成后账号仍可能被删除或者禁用，执行工具再次核对。
            if stream_user is None or stream_user.status !=1:
                yield _sse_line({"type":"error","message":"用户不存在或者已被禁用，请重新登录"})
                return
            async for event in agent_service.stream_agent(db,user=stream_user,data=data,thread_id=data.thread_id):
                public = public_chat_event(event)
                if public is not None:
                    yield _sse_line(public)
    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":"no-cache",
            "Connection":"keep-alive",
            "X-Accel-Buffering" : "no",
        }
    )

@router.post('/kb/search')
def kb_search(data: kbSearchRequest, user: User = Depends(get_current_developer)):
    """调试用：直接看检索结果和分数，用来标定阈值"""
    results = kb_service.search(data.query, data.top_k)
    confidence, level = kb_service.confidence_of(results)
    return Response.success(
        data=kbSearchResponse(confidence=confidence, level=level, result=results)
    )

@router.post('/kb/rebuild')
def kb_rebuild(user: User = Depends(get_current_developer)):
    """改完 data/kb 后调用，重建索引"""
    count = kb_service.build_index()
    kb_service.reload()
    return Response.success(data={"chunks": count})
