from openai import OpenAI
from app.config import settings
from app.branding import PRODUCT_NAME
from app.common.exceptions import BusinessException
import os
from app.schemes.ai import chatRequest,chatMessage
from app.services import kb_service,lab_service,equipment_service
import json

from sqlalchemy.orm import Session

SYSTEM_PROMPT = "你是" + PRODUCT_NAME + """的助手，回答要简洁。
如果下面提供了实验室资料，请依据资料回答规则、安全、文档里的开放时间说明。
查询当前有哪些开放实验室、某实验室有哪些设备时，必须调用工具，不要编造。
你不能替用户提交预约，也不能直接改数据库。
如果用户要预约，请说明去「实验室列表」选择后提交，等待管理员审核。
"""
REFUSE_TEXT = "抱歉，我在知识库里没有找到足够相关的资料。你可以换个说法，或到【实验室列表】查看具体信息。"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_open_labs",
            "description": "查询当前开放中的实验室列表，可以按名称关键字来筛选",
            "parameters": {
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "string",
                        "description": "实验室的名称关键字，可以为空",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_lab_equipments",
            "description": "查询某个实验室下的设备列表",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab_id": {
                        "type": "integer",
                        "description": "实验室 ID",
                    },
                    "keywords": {
                        "type": "string",
                        "description": "设备名称的关键字，可以为空",
                    },
                },
            },
        },
    },
]

def run_tool(db:Session,name:str,arguments:str) ->str:
    try :
        args = json.loads(arguments or "{}")
    except json.JSONDecodeError: 
        return json.dumps({"error":"参数不是合法的json"},ensure_ascii=False)

    try :
        if name =="list_open_labs":
            keywords = (args.get("keywords")or "").strip() or None
            page = int(args.get("page", 1))          # LLM 可传 page
            page_size = int(args.get("page_size", 10))
            result = lab_service.get_lab_page_list(db,page=page,page_size=page_size,keywords=keywords,status=1)
            rows = [
                {
                    "id":item.id,
                    "name":item.name,
                    "location":item.location,
                    "capacity":item.capacity,
                    "open_time":item.open_time,
                    "close_time":item.close_time

                }
                for item in result.list
            ]
            return json.dumps({
                "total":result.total,
                "page":page,
                "page_size":page_size,
                "has_more":result.total >page*page_size,
                "labs":rows},ensure_ascii=False)

        if name =="list_lab_equipments":
            lab_id = args.get("lab_id")
            if not lab_id:
                return json.dumps({"error": "参数缺少实验室 lab_id"}, ensure_ascii=False)
            keywords = (args.get("keywords") or "").strip() or None
            page=int(args.get("page" ,1))
            page_size = int(args.get("page_size" , 10))
            result = equipment_service.get_equipment_page_list(db,page=page,page_size=page_size,lab_id=int(lab_id),keywords=keywords)
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
                for item in result.list
            ]
            return json.dumps({
                            "total":result.total,
                            "page":page,
                            "page_size":page_size,
                            "has_more":result.total >page*page_size,
                            "equipments":rows,
                            },ensure_ascii=False)
        return json.dumps({"error":f"未找到工具：{name}"},ensure_ascii=False)
            
    except Exception as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)

def get_client() ->OpenAI:
    """创建OPENAI的客户端"""
    LLM_API_KEY= os.getenv("SILICONFLOW_API_KEY")
    if not LLM_API_KEY:
        raise BusinessException(message="没有获取到API KEK")
    return OpenAI(api_key=LLM_API_KEY,base_url=settings.LLM_BASE_URL)

def chat(data:chatRequest,db:Session):
    if not data.messages:
        raise BusinessException(message="对话记录为空")
    history= []
    for message in data.messages:
        if message.role in('user','assistant') and message.content.strip():
            history.append(message.model_dump())
    if not history:
        raise BusinessException(message="请输入您要对话的内容")
    
    #只拿最后一条信息做检索，不要把整段历史拼进去
    question = next((item["content"] for item in reversed(history) if item['role'] =='user'),"",)

    if not question:
        raise BusinessException(message="请输入您要对话的内容")

    results = kb_service.search(question)
    confidence,level = kb_service.confidence_of(results)
    print(f"[RAG] top1={confidence} level={level} hits={len(results)}")

    if not results or confidence < kb_service.LOW_CONFIDENCE:
        return {
            "content":REFUSE_TEXT,
            "confidence":confidence,
            "level" : level,
            "sources":results,
        }

    context = "\n\n".join(f"[{i}] 来源：{r['source']} / {r['title']} \n{r['content']}"for i,r in enumerate(results,1))
    system_prompt = SYSTEM_PROMPT  + "\n\n[实验室资料]\n" + context
    messages=[
        chatMessage(role = "system",content = system_prompt).model_dump(),
        *history,
    ]
    client = get_client()
    try :
        for _ in range(3):
            res = client.chat.completions.create(
            model =settings.LLM_MODEL,
            messages=messages,
            tools = TOOLS,
            tool_choice= "auto",
            temperature= 0
             )
            msg = res.choices[0].message
            tool_calls = msg.tool_calls or []
            if not tool_calls:
                content = msg.content
                if not content or not content.strip():
                    raise BusinessException(message="大模型没有返回内容")
                return {
                            "content" : content,
                            "confidence" : confidence,
                            "level": level,
                            "sources" : results,
                        }
            messages.append(
                {
                    "role":"assistant",
                    "content":msg.content or "",
                    "tool_calls":[
                        {
                            "id":call.id,
                            "type":"function",
                            "function" :{
                                "name" : call.function.name,
                                "arguments":call.function.arguments,
                            },
                        }
                        for call in tool_calls
                    ],
                }
            )
            for call in tool_calls:
                result = run_tool(db,name=call.function.name,arguments=call.function.arguments)
                messages.append(
                    {
                        "role":"tool",
                        "content":result,
                        "tool_call_id":call.id
                    }
                )
        res = client.chat.completions.create(
                    model =settings.LLM_MODEL,
                    messages=messages,
                    tools = TOOLS,
                    tool_choice= "none",
                    temperature= 0
                     )
        content = res.choices[0].message.content
        if not content or not content.strip():             
            raise BusinessException(message="大模型没有返回内容")         
            
    except Exception:
        raise BusinessException(message="大模型调用失败，请稍后重试") 

    return {
        "content" : content,
        "confidence" : confidence,
        "level": level,
        "sources" : results,
    }
