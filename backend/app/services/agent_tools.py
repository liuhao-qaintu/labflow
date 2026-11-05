import json

from langchain_core.tools import tool
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.reservation import Reservation

from app.services import kb_service,lab_service,equipment_service,reservation_service
from app.common.exceptions import BusinessException
from datetime import datetime
from app.schemes.reservation import ReservationCreationRequest

def build_tool(db:Session,current_user:User):

    @tool
    def search_kb(query:str) ->str:
        """根据用户的提问进行知识库的查询亦或者是工具调用"""
      
        try:
            return kb_service.search(query=query) or "没有检索到相关资料"
        except Exception as e:
            return json.dumps({"执行结果":False,"error":str(e)},ensure_ascii=False)


    @tool
    def search_open_labs(keywords:str='',) ->str:
        """查询开放的实验室列表"""
        try:
            keywords = keywords.strip() or None
            page = lab_service.get_lab_page_list(
                db=db,
                page=1,
                page_size=10,
                keywords=keywords,
                status=1
            )
            rows = [
                {
                    "id":item.id,
                    "name":item.name,
                    "location":item.location,
                    "open_time":item.open_time,
                    "close_time":item.close_time,
                    "capacity":item.capacity
                }
                for item in page.list
            ]
            return json.dumps({"total":page.total,"labs":rows},ensure_ascii=False)
        except Exception as e:
            return json.dumps({"执行结果":False,"error":str(e)},ensure_ascii=False)

    @tool
    def search_labs_equipment(keywords:str="",lab_id:int | None=None) ->str:
        """查询实验室的设备列表"""
        try:
            keywords = keywords.strip() or ""
            page = equipment_service.get_equipment_page_list(
                db=db,
                lab_id= lab_id,
                keywords=keywords,
                page=1,
                page_size=10,
                )

            rows = [
                {
                    "id":item.id,
                    "name":item.name,
                    "lab_id":item.lab_id,
                    "lab_name":item.lab_name,
                    "spec":item.spec,
                    "quantity":item.quantity,
                    "status":item.status
                }
                for item in page.list
            ]
            return json.dumps({"total":page.total,"rows":rows},ensure_ascii=False)
        except Exception as e :
            return json.dumps({"执行结果":False,"error":str(e)},ensure_ascii=False)

    @tool
    def create_lab_reservation(
        lab_id:int,
        date:str,
        start_time:str,
        end_time:str,
        equipment_id:int | None = None,
        remark:str ='',
    ):
        """创建预约单预约实验室或设备"""
        try:
            data = ReservationCreationRequest(
            lab_id=lab_id,
            equipment_id=equipment_id,
            date=date,
            start_time=start_time,
            end_time=end_time,
            remark=remark
        )
            reservation_service.create_reservation(db=db,current_use=current_user,data=data)

            return json.dumps({
                "结果":True,
                "message":"预约已提交，请等待管理员审核",
                "lab_id":lab_id,
                "equipment_id":equipment_id,
                "date":date,
                "start_time":start_time,
                "end_time":end_time,
                "remark":remark,
            },ensure_ascii=False)
        except BusinessException as e:
            return json.dumps({"结果":False,"error":e.message},ensure_ascii=False)
        except Exception as e:
            return json.dumps({"结果":False,"error":str(e)},ensure_ascii=False)

    @tool
    def get_today():
        """获取今天的日期"""
        now = datetime.now()
        return now.strftime("%Y-%m-%d")

    return [search_kb,search_labs_equipment,search_open_labs,create_lab_reservation,get_today]
    
