from pydantic import BaseModel
from app.schemes.user import UserResponse

class LoginRequest(BaseModel):
    username:str
    password:str

class loginResponse(BaseModel):
    token:str
    user:UserResponse
    
class RegisterRequest(BaseModel):
    username:str
    password:str
    name:str | None = None


