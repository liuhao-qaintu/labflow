# labFLow · 实验室资源协作助手

labFLow 面向实验室资源查询、预约申请与审批管理，将结构化业务数据、规则知识库和自然语言交互整合到统一平台。用户可查询实验室与设备、了解使用规则并发起预约；系统在写入前要求确认，提交后进入管理员审核流程。

## 应用场景

### 学院共享实验室的设备预约

学院的计算机、物理和化学实验室由多个课题组共享。学生需要了解设备和开放时间、查阅使用规则并提交预约；管理员则需要核对申请、安排资源和处理审批。资源信息与使用制度分别维护，申请人经常需要在设备列表、制度说明和预约表单之间切换。

以学生开展深度学习模型训练为例，可以直接向助手提出需求：

> 我想预约计算机实验室的GPU工作站，明天14:00到16:00使用，需要提前审核吗？

平台将这项需求拆分为资源核对、规则咨询和预约提交：

| 环节 | 平台处理 | 用户操作 |
|---|---|---|
| 核对资源 | 查询数据库中的实验室、GPU工作站、设备状态和开放时段，将“明天”转换为具体日期 | 确认目标设备，补充缺失信息 |
| 解释规则 | 从规则知识库检索预约与审核要求，说明提交后的审批流程 | 了解使用条件 |
| 确认申请 | 汇总实验室、设备、日期与起止时间，等待明确确认 | 核对信息后确认，或取消本次申请 |
| 提交与校验 | 用户确认后检查时间、资源状态与预约冲突，符合条件时创建待审核记录 | 查看提交结果；如有冲突，调整时段后重新申请 |
| 管理员审批 | 管理员在后台审核，申请人可查询更新后的预约状态 | 审核通过后按规定使用设备 |

这一流程中，设备状态来自业务数据库，使用制度来自规则知识库，预约写入由用户确认触发，最终使用仍以管理员审核结果为准。平台将规则咨询与预约办理连接起来，并保留清晰的操作边界。

## 核心功能

- **资源管理**：维护实验室、设备、开放时段和使用状态，支持资源查询与预约。
- **预约协作**：提交申请、查看审核结果、取消本人待审核预约，管理员集中处理审批。
- **智能助手**：结合规则检索和数据库查询回答问题，在信息齐全并经用户确认后提交预约。
- **连续交互**：流式返回回答，保存对话执行状态，支持恢复待确认操作。
- **账号与权限**：JWT 身份认证，区分普通用户、资源管理员和维护权限，按用户隔离执行状态。
- **账号恢复**：站内申请、凭据查询、补充材料与管理员核验，重置后首次登录必须修改密码。

## 在参考项目基础上的改进

| 改进方向 | 具体实现 | 作用 |
|---|---|---|
| [MCP 工具接入](backend/app/services/mcp_client.py) | 将日期、实验室和设备查询接入 stdio MCP；写预约工具保留在业务服务，协议服务不可用时回退本地工具 | 分离查询与写入能力，统一工具调用入口 |
| [预约执行控制](backend/app/services/agent_service.py) | 在写入工具前增加 LangGraph interrupt 确认节点，通过异步 SQLite checkpoint 保存状态并恢复；恢复前检查待确认操作 | 用户拒绝时不写入，确认结果与待执行操作对应 |
| [规则检索](backend/app/services/kb_service.py) | 使用 BGE-M3 嵌入与 FAISS；按标题分段，采用500字符切分和50字符重叠，支持文件变更检测与索引重建 | 规则更新后可重建检索数据，减少无依据回答 |
| [用户与维护隔离](backend/app/access.py) | checkpoint 以用户ID和会话ID共同定位；后端校验管理员角色和维护白名单；公开响应过滤内部工具预览 | 避免前端菜单成为权限依据，限制跨用户读取和维护操作 |
| [流式交互处理](frontend/src/router/ai.js) | 使用携带JWT的fetch接收SSE，处理分段数据帧，区分业务完成与连接中断 | 及时展示回答，并在响应异常时给出明确反馈 |
| [站内账号恢复](backend/app/services/recovery_service.py) | 增加申请收件箱、随机凭据、处理时间线和补充材料；核验重置与申请状态同事务提交 | 将申请、核验、处理结果和首次改密串成完整流程，无需外部邮件服务 |
| [登录状态更新](backend/app/utils/jwt.py) | JWT绑定密码版本，密码重置或修改后旧凭证失效；待改密账号在服务端限制业务访问 | 让恢复操作及时反映到已有登录状态 |
| [回归与运行支持](backend/tests) | 增加权限、凭据、事务回滚和初始化测试；提供配置模板、锁定依赖及受保护的示例数据脚本 | 支持重复验证与独立环境配置 |

## 技术栈

| 层次 | 组件 |
|---|---|
| 前端 | Vue 3、JavaScript、Vite、Element Plus、Axios |
| 后端 | FastAPI、SQLAlchemy、MySQL、JWT |
| 智能编排 | LangGraph、OpenAI兼容模型接口、MCP stdio |
| 知识检索 | BGE-M3、FAISS |
| 执行状态 | SQLite、LangGraph checkpoint |

[使用指南](docs/USAGE.md) · [架构设计](docs/ARCHITECTURE.md) · [配置与维护](docs/OPERATIONS.md) · [测试说明](docs/TESTING.md)

## 安装与启动

### 环境要求

- Python 3.12。
- Node.js：22.x版本不低于22.18，或24.12及以上；详见 frontend/package.json 的 engines。
- MySQL 8.0及以上。
- 支持聊天和嵌入接口的模型服务。

以下命令使用 Windows PowerShell，从项目根目录执行。Linux/macOS 可使用 `python3.12 -m venv .venv` 创建环境，后续解释器路径改为 `.venv/bin/python`。

### 安装依赖

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
npm.cmd --prefix frontend ci
```

### 配置服务

在MySQL中创建数据库及专用账号，并授予目标库所需的建表和读写权限。复制配置模板，已有配置时保留原文件：

```powershell
if (!(Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
if (!(Test-Path frontend/.env)) { Copy-Item frontend/.env.example frontend/.env }
```

在 backend/.env 中设置：

| 配置项 | 用途 |
|---|---|
| DATABASE_URL | MySQL连接地址 |
| JWT_SECRET_KEY | 独立随机签名密钥 |
| LLM_BASE_URL、LLM_MODEL | 聊天模型接口及模型名称 |
| SILICONFLOW_API_KEY | 模型服务密钥，由后端读取 |
| PASSWORD_RECOVERY_ADMIN_ID | 找回申请的接收管理员ID |
| RESET_INITIAL_PASSWORD | 管理员重置时使用的初始密码 |
| DEVELOPER_USER_IDS | 可调用维护接口的管理员ID白名单 |

首次启动会创建缺失的数据表，不会创建MySQL数据库或数据库账号。首次管理员账号、示例数据和配置细节见[配置与维护](docs/OPERATIONS.md)。

### 启动后端

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload --reload-dir backend
```

### 启动前端

另开终端，从项目根目录执行：

```powershell
npm.cmd --prefix frontend run dev -- --host 127.0.0.1
```

打开Vite输出的实际地址，默认 http://127.0.0.1:5173。前端模板通过同源代理将 `/router` 和 `/uploads` 转发到后端。分别在对应终端按 Ctrl+C 停止服务。

### 构建前端

```powershell
npm.cmd --prefix frontend run build
```

构建产物位于 frontend/dist。部署时需要配置静态站点与API反向代理；开发代理不会写入构建产物，服务部署关闭 `--reload`。详细要求见[配置与维护](docs/OPERATIONS.md)。

## 知识库维护

规则文档位于 backend/data/kb。按实际实验室制度维护文档，配置可用的嵌入服务后重建索引：

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m app.build_kb
Pop-Location
```

当前嵌入模型为 BAAI/bge-m3。索引保存在 backend/data/rag_index，可通过源文档重建。索引构建及智能问答会向配置的模型服务发送相应内容；模型调用受服务商配额和计费规则约束。

## 项目结构

```text
backend/app/            接口、业务服务、智能编排与数据模型
backend/data/kb/        规则知识文档
backend/tests/          自动化测试与协议检查
backend/init_demo.py    可选示例数据初始化
frontend/src/           页面、路由和API调用
docs/                   使用、架构、维护与测试文档
```

## 参考来源

项目启发于B站UP主程序员青戈的[《FastAPI + LangGraph 从零开发智能实验室预约系统》](https://www.bilibili.com/video/BV13hbP6zEUd)，并在此基础上围绕工具接入、执行控制、权限隔离和账号恢复进行了扩展。第三方依赖说明见[参考来源](THIRD_PARTY_NOTICES.md)。
