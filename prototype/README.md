# Loop 原型运行说明

这是本地网页 → Python HTTP 服务 → Supabase PostgreSQL 的真实数据库原型。前端无云端管理员密码或 API secret；五个演示账号分别使用独立 PostgreSQL LOGIN 角色。数据库函数从 SESSION_USER 推导身份，拒绝前端传入 actor_id 等身份字段。

## 在当前电脑运行

双击 `start.command`，或在本目录执行：

```sh
./start.command
```

打开 http://127.0.0.1:5413 。本地账号密码保存在 `.local/connection.json`；本次工作区另有 `.local/登录信息.md` 便于组员在现场复制。角色 douyin_demo_u1 对应 Demo_Ada，并有固定查询报表权限；u2–u5 可演示不同用户的所有权限制。

密码保存在本机权限 600 的文件中，不能上传课程平台、聊天群或 Git。提交压缩包主动排除了整个 .local 和 .venv，接收者需要自行配置。客户端 Cookie 只保存随机会话标识，数据库凭据只在本地服务内存中使用。服务仅绑定 127.0.0.1，不作为公网托管应用。

## 在另一台电脑或独立新项目复现

要求 Python 3.10+、可访问 Supabase 的网络，以及新建免费项目的管理员连接信息。项目内部默认数据库通常叫 postgres；具体主机必须从该项目 Connect 面板复制，不猜测池化器地址。

在本目录执行：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python setup_demo.py --host '<实际 Direct connection 主机>'
```

脚本交互式读取管理员密码，不保存它；为本项目生成五个受限演示角色的随机密码，随后应用 01、02_final_snapshot、04、05、06 SQL，恢复最终报告对应的 100 条虚构记录。若要使用最初的 69 条教学种子，选择 02_seed 代替快照，不能两份都执行。它发现已有业务 schema 或同名角色会停止，不会清库、覆盖数据或自动轮换密码。若导入中途失败，保留错误和已保存的本地凭据，先排查，不自动重置。

TLS 使用随包提供的 Supabase 公共 CA 和 verify-full，同时校验 CA 与主机名。CA 来源为 Supabase 官方下载域 `https://supabase-downloads.s3-ap-southeast-1.amazonaws.com/prod/ssl/prod-ca-2021.crt`，它不是私钥或登录凭据。如果网络不支持直连 IPv6，请从控制台取得真实 Session pooler 参数，分别调整 .local 配置的 host、port 和用户名格式；当前验证使用 Direct connection，不把池化模式写成已测结果。

Windows 可用 `.venv\Scripts\python.exe` 执行同一套 Python 文件；start.command 是 macOS 启动入口。

## 功能与可验证性

- 数据库账号登录、退出和过期会话；HTTP 同源检查、HttpOnly/SameSite Cookie 和 CSRF token。
- 视频浏览与搜索、发布元数据、修改自己的文案、隐藏/恢复、添加话题。
- 点赞/取消点赞、关注/取消关注、评论和同视频回复。
- 创建收藏夹、收藏/移除项目、自动分配夹内编号。
- 操作员账号执行固定白名单的 10 项 SELECT 报表。
- 播放随包的原创合成 WebM；媒体文件不写入关系表。种子 URL 是 example.invalid，界面明确用本地示例片段展示播放器，不声称它是种子记录对应的真实抖音视频。

移除项目、取消点赞或关注只在用户主动点击时改变其当前关联；原型不提供删账号、删视频、删评论、清库或重置按钮。

## 测试

```sh
.venv/bin/python tests/test_business.py
```

21 项测试连接真实 PostgreSQL，并包括两个并发事务。一般写入探测结束时回滚；并发测试新建的专用记录会保留用于审计，不删除现有数据。重复测试会增加带 Concurrency verification 标签的虚构记录，不要在真实用户项目运行。

`tests/browser.cjs` 使用 Playwright 执行真实浏览器流程。需要另外提供 Playwright，当前验证使用 Codex 内置的 Node/Playwright 和既有 Chromium；本项目生产运行不依赖 Node。可通过 PLAYWRIGHT_MODULE 与 PLAYWRIGHT_EXECUTABLE_PATH 指定测试模块和浏览器位置。浏览器测试新建的演示记录保留，不删除旧数据。

## 限制

这是数据库课程演示，不包括开放注册、找回密码、生产认证、媒体上传/转码、推荐或版权管理。原型使用固定的五个受控数据库账号；角色管理和 schema 所有者是可信管理员。RLS 保持默认拒绝，只有私有 schema 的有限函数被授予演示角色执行权限。不要把这些账号用于其他数据，或将本地开发服务器公开到网络。
