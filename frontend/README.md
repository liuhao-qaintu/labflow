# labFLow 前端

基于Vue 3、JavaScript、Vite和Element Plus构建，提供资源查询、预约协作、智能助手、账号恢复和管理页面。

## 环境与配置

Node.js版本要求见package.json的engines，依赖按package-lock.json安装。首次配置可将.env.example复制为.env；已有配置文件保持不变。

VITE_API_BASE_URL默认留空，通过Vite将/router、/uploads代理到后端。使用独立API域名时，需同步配置后端CORS。VITE_变量会进入客户端，不应存放服务密钥。

## 开发与构建

在frontend目录执行：

```powershell
npm.cmd ci
npm.cmd run dev -- --host 127.0.0.1
```

打开Vite输出的地址；按Ctrl+C停止。构建使用`npm.cmd run build`，产物位于dist；部署时需设置SPA路由回退和API反向代理。

前端测试使用`node --test tests/*.test.js`。前端路由守卫用于导航，角色权限和首次改密限制由后端校验。完整安装见[项目README](../README.md)。
