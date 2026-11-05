from pydantic import BaseModel

class chatMessage(BaseModel):
    role:str
    content:str

class chatRequest(BaseModel):
    messages:list[chatMessage]
    thread_id:str | None = None      #会话id，用于checkpoint恢复；不传由后端生成

class resumeRequest(BaseModel):
    thread_id:str
    approved:bool
    reason:str = ""

class chatSoure(BaseModel):
    content:str
    source:str
    title:str
    score:float

class chatResponse(BaseModel):
    role:str = "assistant"
    content:str
    confidence : float
    level:str
    sources:list[chatSoure] =[]

class kbSearchRequest(BaseModel):
    query:str
    top_k:int = 4

class kbSearchResponse(BaseModel):
    confidence:float
    level:str
    result:list[chatSoure]