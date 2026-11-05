from pydantic import BaseModel,ConfigDict

class LabResponse(BaseModel):
    id:int
    name:str
    description:str |None =None
    location:str|None = None
    open_time:str|None = None
    close_time:str|None = None
    img:str |None =None
    capacity:int
    status:int

    model_config = ConfigDict(from_attributes= True)

class LabCreateRequest(BaseModel):
    name:str
    description:str |None = None
    location:str|None = None
    open_time:str|None = None
    close_time:str|None = None
    img:str |None =None
    capacity:int=0
    status:int=1

class LabUpdateRequest(BaseModel):
    name:str |None = None
    description:str |None = None
    location:str|None = None
    open_time:str|None = None
    close_time:str|None = None
    img:str |None =None
    capacity:int | None = None
    status:int | None = None
    