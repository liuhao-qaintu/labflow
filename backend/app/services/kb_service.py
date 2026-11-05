from app.config import  BASE_DIR
from pathlib import Path
from app.common.llm import get_client
from app.common.exceptions import BusinessException

import faiss
import json
import os
import threading
import numpy as np
import re

KB_DIR = BASE_DIR / 'data' / "kb"
INDEX_DIR = BASE_DIR / "data" / "rag_index"
INDEX_PATH = INDEX_DIR / "index.faiss"
CHUNKS_PATH = INDEX_DIR / "chunks.json"

EMBEDDING_MODEL = "BAAI/bge-m3"
BATCH_SIZE = 16
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

TOP_K =4
HIGH_CONFIDENCE = 0.6
LOW_CONFIDENCE = 0.45

_cache = None
_lock = threading.Lock()

def _embed (texts:list[str]) ->np.ndarray:
    vectors = []
    for i in range (0,len(texts),BATCH_SIZE):
        batch = texts[i:i+BATCH_SIZE]
        resp = get_client().embeddings.create(
            model = EMBEDDING_MODEL,
            input=batch
        )
        vectors.extend(item.embedding for item in resp.data)

    arr = np.array(vectors,dtype="float32")
    faiss.normalize_L2(arr)
    return arr


def _spilt_text(text:str) -> list[str] :
    sections = re.split(r"\n(?=#{1,6}\s)",text)
    chunks = []
    for section in sections:
        section  = section.strip()
        if not section:
            continue
        if len(section) <= CHUNK_SIZE:
            chunks.append(section)
            continue
        start = 0
        while start< len(section):
            chunks.append(section[start:start+CHUNK_SIZE])
            start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks

def build_index() -> int:
    files = sorted(KB_DIR.glob("*.md"))
    if not files:
        raise BusinessException(message= f"{KB_DIR}下没有md文件")
    
    chunks = []
    for path in files :
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            continue
        for piece in _spilt_text(text):
            first_line = piece.splitlines()[0].lstrip("#").strip()
            chunks.append({
                "text":piece,
                "source":path.name,
                "title":first_line[:30],
            })

    if not chunks :
        raise BusinessException(message="知识文档为空")

    vectors = _embed([c["text"] for c in chunks])
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    INDEX_DIR.mkdir(parents=True,exist_ok=True)
    #不用faiss.write_inde避免中文路径问题
    INDEX_PATH.write_bytes(faiss.serialize_index(index).tobytes())
    CHUNKS_PATH.write_text(
        json.dumps(chunks,ensure_ascii=False,indent=2),
        encoding="utf-8",
    )
    return len(chunks)


def _load ():
    """加载索引，不存在就建一次"""
    if not INDEX_PATH.exists() or not CHUNKS_PATH.exists():
        build_index()

    index = faiss.deserialize_index(
        np.frombuffer(INDEX_PATH.read_bytes(),dtype='uint8')
    )
    chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    return index,chunks


def _get_kb():
    """进程内只加载一次：FastAPI同步路由跑在线程池里，加锁保险"""
    global _cache
    if _cache is None:
        with _lock:
            if _cache is None:
                _cache = _load()

    return _cache

def reload():
    """重建索引后清缓存"""
    global _cache
    _cache =None


def needs_rebuild() ->bool:
    """索引不存在、文档增删、或 md 比索引新时，需要重建"""
    if not INDEX_PATH.exists() or not CHUNKS_PATH.exists():
        return True

    current = {p.name for p in KB_DIR.glob("*.md")}
    if not current:
        return True

    indexed = {
        c["source"]
        for c in json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    }
    if current != indexed:
        return True

    index_mtime = min(INDEX_PATH.stat().st_mtime, CHUNKS_PATH.stat().st_mtime)
    return any(p.stat().st_mtime > index_mtime for p in KB_DIR.glob("*.md"))

def ensure_index() -> int | None:
    """启动时调用：只在需要时重建；没重建返回 None"""
    if not needs_rebuild():
        return None
    count = build_index()
    reload()
    return count

def search(query:str,top_k:int = TOP_K) ->list[dict]:
    """检索 top-k，返回内容、来源、标题、余弦得分"""
    index ,chunks = _get_kb()
    q = _embed([query])
    scores,ids = index.search(q,top_k)

    results = []
    for score,idx in zip(scores[0],ids[0]):
        if idx ==-1 :       #候选不足时faiss才会补-1
            continue
        chunk = chunks[int(idx)]
        results.append({
            "content":chunk["text"],
            "source": chunk["source"],
            "title":chunk["title"],
            "score":round(float(score),4)
        })

    return results


def confidence_of (results:list[dict]) ->tuple[float,str]:
    """用 top1 余弦分数作为整体置信度（不是概率，阈值要实测标定）"""
    if not results :
        return 0.0,"low"
    top1 = max(0.0,min(1.0,results[0]["score"]))
    if top1 >=HIGH_CONFIDENCE:
        level ="high"
    elif top1>=LOW_CONFIDENCE:
        level = "medium"
    else:
        level = "low"
    return round(top1,4),level


