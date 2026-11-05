from typing import Literal
from pydantic import BaseModel,ConfigDict

class UserResponse(BaseModel):
    id:int
    username:str
    name:str
    role:str
    email:str|None = None
    phone:str|None = None
    avatar:str |None =None
    status:int
    must_change_password:bool = False
    can_reset_password:bool = False

    model_config = ConfigDict(from_attributes= True)

class PasswordUpdateRequest(BaseModel):
    old_password: str
    new_password: str


class PasswordResetRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    identity_verified: Literal[True]


class UserCreateRequest(BaseModel):
    username:str
    password:str = "123"
    name:str | None = None
    role:str ="student"
    email:str|None = None
    phone:str|None = None
    avatar:str |None =None
    status:int = 1

class UserUpdateRequest(BaseModel):
    name:str | None = None
    role:str | None =None
    email:str|None = None
    phone:str|None = None
    avatar:str |None =None
    status:int = 1  
