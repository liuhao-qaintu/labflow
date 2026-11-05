from app.services.kb_service import build_index

if __name__ == "__main__":
    print(f"索引构建完成：{build_index()} 个 chunk")