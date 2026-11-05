# 配置与维护

## 账号和数据库初始化

创建MySQL数据库与专用账号，在backend/.env中设置DATABASE_URL。服务启动时创建缺失表，不创建数据库或数据库账号。首次管理员账号可先通过注册建立，再由数据库维护者核对具体用户ID，将该账号的role设为admin；维护白名单仍需单独配置。

backend/init_demo.py提供可选示例数据，只允许空的labflow_demo库，包含示例账号与资源。该脚本不用于初始化已有业务库：

```powershell
.\.venv\Scripts\python.exe backend/init_demo.py --confirm-demo-database labflow_demo
```

使用前将DATABASE_URL指向labflow_demo。密码通过交互输入；脚本遇到已有数据会拒绝执行，不提供清空或覆盖开关。初始化输出管理员ID，可用于PASSWORD_RECOVERY_ADMIN_ID配置。

## 配置项

- JWT_SECRET_KEY使用独立、足够长的随机密钥，保存在服务端。修改后原JWT失效。
- SILICONFLOW_API_KEY由统一Settings读取，不放入前端环境变量。
- PASSWORD_RECOVERY_ADMIN_ID指定找回申请的接收管理员；该账号必须处于正常状态。
- DEVELOPER_USER_IDS默认留空，维护操作同时要求管理员角色和白名单授权。
- ENABLE_API_DOCS默认false，本地维护需要时显式打开并重启，接口文档地址为/docs。

## 反向代理与进程

前端构建产物为frontend/dist，静态站点需将前端路由回退到index.html，并将/router与/uploads转发给后端。运行服务时关闭开发热重载，按部署环境设置进程托管、HTTPS、日志轮转与备份。

Vite同源代理用于开发；使用前端配置直连后端时，需把实际前端域名加入后端CORS允许列表。CORS不替代服务端身份与角色检查。

MCP使用后端解释器启动独立stdio进程，显式传递必要配置；仅提供日期、实验室和设备查询。协议服务不可用时，助手使用本地查询工具。

## 数据与知识库

- MySQL保存账号、实验室、设备、预约和找回申请及处理事件。
- backend/data/checkpoints.sqlite保存图执行状态，按用户与会话隔离。
- backend/data/rag_index保存可重建的向量索引，原始规则位于backend/data/kb。
- backend/uploads只提供头像和资源图片，属于公开媒体目录。

备份业务数据库、规则文档及需要保留的执行状态。修改规则后重建索引；文档中的开放制度与服务端时段校验应保持一致。

## 当前运行约束

账号恢复目前使用RESET_INITIAL_PASSWORD指定的统一初始密码，核验重置后首次登录强制改密；面向外部用户部署时，应将其调整为每次重置生成独立临时密码。申请凭据30天到期不等于数据库记录自动删除，记录保留策略需单独配置和执行。

公开凭据查询按进程内来源限频，多实例运行应使用共享限流存储。用户名唯一性目前依赖应用查询，数据库并发约束需在多实例使用前补齐。

预约按实验室/设备分别检查时段重叠，设备数量尚未用于容量控制。工作日与周末制度需结合实际规则校验；当前服务端主要校验资源开放时段。调整业务约束时，同步更新规则知识库和相关测试。
