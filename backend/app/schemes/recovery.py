from typing import Literal
import re
from pydantic import BaseModel,ConfigDict,Field,SecretStr,field_validator


class RecoverySubmitRequest(BaseModel):
    model_config = ConfigDict(extra='forbid',str_strip_whitespace=True)
    username:str = Field(min_length=1,max_length=50)
    name:str = Field(default='',max_length=50)
    email:str = Field(default='',max_length=100)
    phone:str = Field(default='',max_length=30)
    description:str = Field(default='',max_length=1500)

    @field_validator('email')
    @classmethod
    def valid_email(cls,value):
        if value and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',value):
            raise ValueError('邮箱格式不正确')
        return value

    @field_validator('phone')
    @classmethod
    def valid_phone(cls,value):
        if value and not re.fullmatch(r'[+0-9 ()-]{5,30}',value):
            raise ValueError('手机号格式不正确')
        return value


class RecoveryLookupRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    credential:SecretStr

    @field_validator('credential')
    @classmethod
    def valid_credential(cls,value):
        if not re.fullmatch(r'[A-Za-z0-9_-]{43}',value.get_secret_value()):
            raise ValueError('申请凭据格式不正确')
        return value


class RecoverySupplementRequest(RecoveryLookupRequest):
    content:str = Field(min_length=1,max_length=1500)

    @field_validator('content')
    @classmethod
    def valid_content(cls,value):
        if not value.strip():
            raise ValueError('请填写补充说明')
        return value.strip()


class RecoveryHandleRequest(BaseModel):
    model_config = ConfigDict(extra='forbid',str_strip_whitespace=True)
    action:Literal['need_more_info','reject','reset']
    message:str = Field(min_length=1,max_length=1500)
    identity_verified:bool = False
    target_user_id:int | None = None
