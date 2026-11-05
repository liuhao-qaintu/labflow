"""服务端用户边界与面向使用者的事件投影；不返回内部工具预览。"""
from pathlib import PurePosixPath

from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles

PUBLIC_IMAGE_EXTENSIONS = frozenset({'.jpg', '.jpeg', '.png', '.gif', '.webp'})


def user_checkpoint_config(thread_id, user_id):
    if type(user_id) is not int or user_id <= 0 or not isinstance(thread_id, str) or not 1 <= len(thread_id) <= 128:
        raise ValueError('无效的用户或会话标识')
    return {'configurable': {'thread_id': f'user:{user_id}:{thread_id}'}, 'recursion_limit': 10}


def public_chat_event(event):
    kind = event.get('type')
    if kind == 'thread':
        return {'type': kind, 'thread_id': event.get('thread_id')}
    if kind in {'status', 'tool_start', 'tool_end'}:
        return {'type': 'status', 'message': '正在核对资源与使用规则…'}
    if kind == 'token':
        return {'type': kind, 'content': event.get('content', '')}
    if kind == 'interrupt':
        args = (event.get('payload') or {}).get('args') or {}
        allowed = ('lab_id', 'equipment_id', 'date', 'start_time', 'end_time', 'remark')
        return {'type': kind, 'thread_id': event.get('thread_id'),
                'payload': {'question': '请核对预约信息，确认后再提交。',
                            'args': {key: args[key] for key in allowed if key in args}}}
    if kind == 'done':
        return {'type': kind}
    if kind == 'error':
        return {'type': kind, 'message': '本次请求未完成，请稍后重试或重新发起咨询。'}
    return None


class PublicImageFiles(StaticFiles):
    """头像和资源图片是公开媒体；不把历史PDF、备份或办公文件作为静态文件提供。"""
    async def get_response(self, path, scope):
        name = PurePosixPath(path)
        if len(name.parts) != 1 or name.suffix.lower() not in PUBLIC_IMAGE_EXTENSIONS:
            raise HTTPException(status_code=404)
        return await super().get_response(path, scope)
