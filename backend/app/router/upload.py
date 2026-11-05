import os 
import shutil
import time
import uuid
from pathlib import Path
from fastapi import APIRouter, File, UploadFile, Depends
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.access import PUBLIC_IMAGE_EXTENSIONS


from app.common.response import Response
from app.common.exceptions import BusinessException
from app.config import ALLOW_EXTENSIONS,MAX_FILE_SIZE,UPLOAD_DIR
router = APIRouter(prefix='/files',tags=["文件管理"])

@router.post('/upload')
def upload(file:UploadFile = File(...), user: User = Depends(get_current_user)):
    """文件上传的接口"""
    if not file.filename:
        raise BusinessException(message = "文件名不能为空")


    orignal_name=os.path.basename(file.filename)
    ext = Path(orignal_name).suffix.lower()
    if ext not in PUBLIC_IMAGE_EXTENSIONS:
        raise BusinessException(message = f"文件名的类型不对:{ext}")

    header = file.file.read(16)
    file.file.seek(0)
    valid = ((ext in {'.jpg', '.jpeg'} and header.startswith(b'\xff\xd8\xff'))
             or (ext == '.png' and header.startswith(b'\x89PNG\r\n\x1a\n'))
             or (ext == '.gif' and header.startswith((b'GIF87a', b'GIF89a')))
             or (ext == '.webp' and header[:4] == b'RIFF' and header[8:12] == b'WEBP'))
    if not valid:
        raise BusinessException(message="仅支持有效的头像或资源图片")

    if file.size and file.size > MAX_FILE_SIZE :
        raise BusinessException(message = f"文件大小不可以超过 {MAX_FILE_SIZE// 1024 // 1024 }")

    disk_name = f"{int(time.time())*1000}_{uuid.uuid4().hex[:8]}{ext}"

    save_path = UPLOAD_DIR / disk_name

    with open(save_path,"wb") as f :
        shutil.copyfileobj(file.file,f)

    return Response.success(
        data={
            "orginal_name":orignal_name,
            "disk_name": disk_name,
            "size":file.size,
            "url":f"/uploads/{disk_name}"
        }
    )
