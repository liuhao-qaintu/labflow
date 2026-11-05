from fastapi import HTTPException,Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.common.response import Response

class BusinessException(Exception):

    def __init__(self, message:str, code:int =500):
        self.message = message
        self.code = code
        super().__init__(message)

async def business_exception_handler(request:Request,exc:BusinessException):
    return JSONResponse(
        status_code=200,
        content=Response.error(code = exc.code,message = exc.message).model_dump()
    )

async def http_exception_handler(request:Request,exc:HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=Response.error(code = exc.status_code,message = exc.detail).model_dump(),
    )

async def validation_exception_handler(request:Request,exc:RequestValidationError):
    # 校验错误只返回字段位置和说明，不能回显密码、重置凭证或整个请求体。
    errors = [{key: item[key] for key in ('loc', 'msg', 'type') if key in item} for item in exc.errors()]
    return JSONResponse(
        status_code=422,
        content=Response.error(code = 422,message = "请求参数校验错误",data=errors).model_dump(),
    )
async def global_exception_handler(request:Request,exc:Exception):
    return JSONResponse(
        status_code=500,
        content=Response.error(code = 500,message = "服务器内部错误").model_dump(),
    )
