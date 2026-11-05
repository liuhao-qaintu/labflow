"""实验室只读工具的 MCP Server（stdio 传输）。

只暴露查询类工具；写预约刻意不在这里暴露——写操作留在 Agent 侧，
由 confirm 节点 + interrupt 强制人工确认，权限边界不因为接了 MCP 而放宽。
"""
import json
from datetime import datetime

from mcp.server.mcpserver import MCPServer

from app.database import SessionLocal
from app.services import equipment_service, lab_service

server = MCPServer(
    "lab-tools",
    instructions="实验室只读查询工具：查开放实验室、查设备、取当天日期。",
)


@server.tool()
def get_today() -> str:
    """获取今天的日期，格式 YYYY-MM-DD。"""
    return datetime.now().strftime("%Y-%m-%d")


@server.tool()
def search_open_labs(keywords: str = "") -> str:
    """查询开放的实验室列表；keywords 可选，用于按名称或位置过滤。"""
    with SessionLocal() as db:
        page = lab_service.get_lab_page_list(
            db=db, page=1, page_size=10, keywords=keywords.strip() or None, status=1
        )
        rows = [
            {
                "id": item.id,
                "name": item.name,
                "location": item.location,
                "open_time": item.open_time,
                "close_time": item.close_time,
                "capacity": item.capacity,
            }
            for item in page.list
        ]
        return json.dumps({"total": page.total, "labs": rows}, ensure_ascii=False)


@server.tool()
def search_labs_equipment(keywords: str = "", lab_id: int | None = None) -> str:
    """查询实验室设备；可按 lab_id 过滤。"""
    with SessionLocal() as db:
        page = equipment_service.get_equipment_page_list(
            db=db, lab_id=lab_id, keywords=keywords.strip(), page=1, page_size=10
        )
        rows = [
            {
                "id": item.id,
                "name": item.name,
                "lab_id": item.lab_id,
                "lab_name": item.lab_name,
                "spec": item.spec,
                "quantity": item.quantity,
                "status": item.status,
            }
            for item in page.list
        ]
        return json.dumps({"total": page.total, "rows": rows}, ensure_ascii=False)


if __name__ == "__main__":
    server.run()
