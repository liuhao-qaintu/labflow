# 测试说明

## 后端

完成环境与配置后，从项目根目录执行：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests -p 'test_*.py' -v
.\.venv\Scripts\python.exe backend/tests/check_hitl_checkpoint.py
.\.venv\Scripts\python.exe backend/tests/check_stream_hitl.py
```

单元测试覆盖角色权限、用户归属、公开响应、申请凭据、密码版本、处理事务和初始化保护，使用内存数据库。确认流程检查使用测试模型与工具，验证确认、拒绝、中断保存和恢复。

## MCP协议

```powershell
.\.venv\Scripts\python.exe backend/tests/check_mcp.py
```

该检查启动真实stdio子进程并读取配置的数据库，验证工具发现、调用和Agent接入；Agent部分使用测试模型。应在隔离测试配置和数据上运行。

## 前端

在frontend目录执行：

```powershell
node --test tests/*.test.js
npm.cmd run build
```

检查路由与凭据输入边界，并验证生产构建。

## 回归场景

- 用户拒绝确认时不创建预约；确认后创建待审核记录。
- 不同用户无法读取或恢复彼此的执行状态，普通用户无法调用管理员或维护接口。
- 找回申请仅由指定管理员读取和处理，凭据过期、错误目标与重复处理均被拒绝。
- 密码变化使旧登录失效；完成改密后原申请停止显示初始密码。
- 初始化遇到已有数据时拒绝，不能覆盖账号或预约。

内存数据库和测试模型的结果用于逻辑回归；MySQL并发、跨资源预约约束和实际模型质量应分别在对应环境验证。
