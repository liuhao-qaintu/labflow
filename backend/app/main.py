import asyncio
from contextlib import AsyncExitStack, asynccontextmanager

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from fastapi import FastAPI,HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from app.models.user import User
from app.models.lab import Lab
from app.models.equipment import Equipment
from app.models.reservation import Reservation
from app.database import initialize_database
from app.router import router
from app.config import UPLOAD_DIR
from app.config import settings
from app.branding import PRODUCT_NAME
from app.access import PublicImageFiles
from app.common.exceptions import(
    BusinessException,
    business_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    global_exception_handler,
)
from starlette.middleware.cors import CORSMiddleware 
from app.services.reservation_service import run_expire_scan
from app.services import kb_service, agent_service
from app.services.mcp_client import mcp_client

initialize_database() #建表，并为已有用户表补充改密标记

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(
        run_expire_scan()
    )
    try:
        try:
            count = await asyncio.to_thread(kb_service.ensure_index)
            if count is not None:
                print(f"[知识库]索引已构建：{count}个chunk")
            else :
                print("[知识库]索引已是最新")
        except Exception as e :
            print(f"[知识库] 索引构建失败，首次提问时会重试：{e}")
        try:
            tools = await mcp_client.start()
            print(f"[MCP] 只读工具已接入：{', '.join(tool.name for tool in tools)}")
        except Exception as e:
            print(f"[MCP] 启动失败，回退本地工具：{e}")
        #图里的节点是 async def，存档必须用异步 saver；退出时由 AsyncExitStack 关闭
        async with AsyncExitStack() as stack:
            saver = await stack.enter_async_context(
                AsyncSqliteSaver.from_conn_string(str(agent_service.CHECKPOINT_DB))
            )
            await saver.setup()
            agent_service.ASYNC_CHECKPOINTER = saver
            print("[checkpoint] AsyncSqliteSaver 已就绪")
            yield
    finally:
        agent_service.ASYNC_CHECKPOINTER = None
        await mcp_client.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass



app = FastAPI(title=PRODUCT_NAME, lifespan=lifespan,
              docs_url='/docs' if settings.ENABLE_API_DOCS else None,
              redoc_url=None, openapi_url='/openapi.json' if settings.ENABLE_API_DOCS else None)
app.include_router(router)
app.add_exception_handler(BusinessException,business_exception_handler)
app.add_exception_handler(HTTPException,http_exception_handler)
app.add_exception_handler(RequestValidationError,validation_exception_handler)
app.add_exception_handler(Exception,global_exception_handler)
app.mount("/uploads",PublicImageFiles(directory=UPLOAD_DIR),name="uploads")

@app.get('/')
def root():
    return {"message":"FastAPI正在运行中"}  


origins = [
    "http://localhost:5175",
    "http://127.0.0.1:5175"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
