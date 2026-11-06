# 配置与维护

## 账号和数据库初始化

创建 MySQL 数据库与专用账号，在 `backend/.env` 中设置 `DATABASE_URL`。服务启动时创建缺失表，不创建数据库或数据库账号。

首次管理员可先通过注册建立账号，再由数据库维护者核对具体用户 ID，将该账号的 `role` 设为 `admin`。维护白名单和恢复申请接收人仍需单独配置。

`backend/init_demo.py` 提供可选示例数据，只允许空的 `labflow_demo` 库，包含示例账号与资源：

```powershell
.\.venv\Scripts\python.exe backend/init_demo.py --confirm-demo-database labflow_demo
```

使用前将 `DATABASE_URL` 指向 `labflow_demo`。密码通过交互输入；遇到已有数据时拒绝执行，不提供清空或覆盖开关。初始化输出的管理员 ID 可用于 `PASSWORD_RECOVERY_ADMIN_ID`。

## 配置项

| 配置项 | 用途 |
| --- | --- |
| `DATABASE_URL` | 数据库连接地址，仅保存于后端配置 |
| `JWT_SECRET_KEY` | 独立随机签名密钥；修改后原 JWT 失效 |
| `JWT_EXPIRE_HOURS` | 登录凭据有效时长 |
| `LLM_BASE_URL`、`LLM_MODEL` | 兼容模型接口与聊天模型名称 |
| `SILICONFLOW_API_KEY` | 模型服务密钥，由后端读取 |
| `PASSWORD_RECOVERY_ADMIN_ID` | 正常状态的恢复申请接收管理员 |
| `RESET_INITIAL_PASSWORD` | 管理员核验重置后交付的初始密码 |
| `DEVELOPER_USER_IDS` | 维护接口白名单，默认留空 |
| `ENABLE_API_DOCS` | 默认关闭；本地维护显式开启并重启后访问 `/docs` |

模板位于 [backend/.env.example](../backend/.env.example) 和 [frontend/.env.example](../frontend/.env.example)。不要将后端密钥填入前端变量或提交真实配置。

## 开发与服务部署

开发时优先使用 Vite 同源代理，将 `/router` 和 `/uploads` 转发到后端。若配置为前端直连后端，需将实际前端地址加入 CORS 允许列表；身份和角色仍由服务端校验。

构建产物为 `frontend/dist`。部署时配置静态站点、前端路由回退到 `index.html`，并将 API 与公开媒体请求转发到后端。关闭开发热重载，按环境配置 HTTPS、进程托管、日志轮转和备份。

MCP 使用后端解释器启动独立 stdio 进程，仅暴露日期、实验室和设备查询。确认执行环境能够启动子进程，并保持必要配置一致。

## 规则更新与索引重建

1. 在 `backend/data/kb` 维护实际预约、安全和设备使用制度。
2. 核对规则与服务端时段校验保持一致。
3. 配置可用的嵌入服务，重建并重新加载索引。

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m app.build_kb
Pop-Location
```

具备维护权限的账号也可调用知识库重建接口。当前嵌入模型为 `BAAI/bge-m3`，向量索引位于 `backend/data/rag_index`，可以从规则文档重建。

索引构建和智能问答会向配置的模型服务发送相应内容。外部请求使用服务商的额度及计费规则，不把真实账号凭据写入规则文档或提示内容。

## 数据备份与公开媒体

| 应保留或备份 | 可从来源重建 | 按公开媒体处理 |
| --- | --- | --- |
| MySQL 业务数据、恢复申请及事件 | `backend/data/rag_index` | `backend/uploads` |
| 规则文档 | 根据规则重新生成的向量 | 用户头像与资源展示图片 |
| 需要继续使用的 checkpoint |  |  |

恢复申请凭据仅以哈希保存；申请材料和处理记录属于业务数据。申请凭据到期不等于数据库记录自动删除，保留与清理策略需单独安排。

## 当前运行约束

账号恢复使用 `RESET_INITIAL_PASSWORD` 指定的统一初始密码，首次登录强制改密。面向外部用户部署时，应调整为每次重置生成独立临时密码；这是部署前的调整事项，当前实现尚未替换该策略。

公开凭据查询使用进程内来源限频；多实例运行应采用共享限流存储。用户名唯一性依赖应用查询，数据库并发约束需在多实例使用前补齐。

预约按实验室或设备分别检查时段重叠，设备数量尚未用于容量控制。跨资源预约和工作日、周末制度应结合实际管理规则验证，当前主要校验资源开放时段。

调整业务约束时，同步更新规则知识库和相关测试。验证命令见[测试说明](TESTING.md)。
