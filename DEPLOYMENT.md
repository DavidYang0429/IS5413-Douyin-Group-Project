# Vercel 在线部署

这次适配解决本地 Python 进程关闭导致网站离线，以及服务器实例重启后内存会话丢失的问题。课程报告记录的是最初本地验收版本；云端适配的会话机制与部署验证在本文单独记录。业务表结构、数据库身份和事务规则不变。

## 平台配置

- Git 仓库的 Root Directory 选 `prototype`。
- 使用 `prototype/vercel.json`：Python API Functions 和 CDN 静态资源，区域 sin1。
- `build_static.py` 只复制浏览器资源到 public，不复制私有配置、测试或虚拟环境。
- 不需要在自己的电脑上持续运行服务；GitHub 本身只提供代码和文档。

## 服务端 Secret

在 Vercel 项目中配置以下 Secret，不能以 NEXT_PUBLIC 或其他公开变量形式设置，也不能写入 GitHub：

- `LOOP_CONNECTION_JSON`：与本机 .local/connection.json 相同结构的连接配置和受限角色密码。连接池需要时可额外指定 username_suffix；不要猜测主机名。
- `LOOP_SESSION_KEY`：独立生成、至少 32 字符的随机签名密钥，在同一环境的各次函数调用中保持一致。

这里只使用五个受限演示账号，不使用数据库管理员或 Supabase service-role 密钥。数据库连接仍校验 TLS CA 和主机名，且每次调用完成即关闭连接。

## 会话与访问

签名 Cookie 只含受保护的身份、CSRF token、过期时间和凭据版本，不含数据库密码。数据库密码只存在服务端配置中。Cookie 一小时过期；云端带 Secure、HttpOnly、SameSite=Strict。函数冷启动或实例切换不会自动丢失会话，签名密钥或受限角色密码变更会使旧 Cookie 失效。退出登录清除当前浏览器 Cookie；此课程原型不实现分布式单会话撤销列表。

POST 请求核对同源 Origin 和 Host，并保留 CSRF 校验。远程访问需要和本地相同的演示账号密码，不能因为网站公开就公开数据库凭据。

Supabase 免费项目低活跃时仍可能暂停，Vercel 免费托管不能消除这个数据库限制。演示前应实际登录并运行一项报表。本项目不添加定时保活或付费升级。

## 验证入口

- `prototype/tests/test_sessions.py`：签名篡改、过期、密码轮换、跨实例恢复等回归测试。
- `prototype/tests/test_session_restart.py`：真实数据库登录后完整重启 HTTP 服务，验证原 Cookie 与数据库查询仍有效，并验证 CSRF、Origin 和退出行为。
