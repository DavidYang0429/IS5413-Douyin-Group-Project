# 五分钟演示与答辩

本稿配合实际原型和 16 页 Final Report。全程使用虚构课程数据；实际课堂演示由小组完成。

## 演示前十分钟

1. 检查 Supabase 项目 ACTIVE_HEALTHY；免费项目若已暂停，先在控制台恢复并实际执行一条 SELECT。
2. 双击 prototype/start.command，打开 http://127.0.0.1:5413 。从本机 prototype/.local/登录信息.md 复制 u1 的密码，不在投屏时展示密码文件。
3. 登录 Demo_Ada，确认播放器能播放，SQL reports 的 Q03 能返回真实数据。
4. 将报告打开到 ER 图和第 14 节测试总结。展示界面时浏览器缩放 90–100%，关闭无关标签页。
5. 本次演示使用新的收藏夹名称，例如 Demo 加当天时分，避免同一用户重名。不要为了演示清空旧数据。

## 时间与英文讲稿

| 时间 | 操作 | 建议英文说明 |
| --- | --- | --- |
| 0:00–0:35 | 展示报告第 2–4 节 | We designed a short video database with ten entities. Associative and weak entities count toward that limit. Comments have a recursive parent, and collection items use a local partial key. |
| 0:35–1:10 | 登录并浏览 Explore | This browser talks to a local Python service and a real Supabase PostgreSQL database. Each demo account has a separate database login. The actor is derived from SESSION_USER, not a user ID supplied by the browser. |
| 1:10–1:50 | Publish a video，文案填 Classroom demonstration，默认媒体位置，发布 | Publishing creates a real row with a generated primary key. Media stays outside relational tables. This bundled clip is an original placeholder, not an actual Douyin video. |
| 1:50–2:30 | 新视频点 Comments，发评论，再点 Reply 发回复；点赞 | A reply must reference an existing comment on the same video. The database rejects cross video replies and preserves immutable ancestry. Likes use a composite key to prevent duplicates. |
| 2:30–3:10 | My collections 新建唯一名称；回 Explore 将新视频 Save 到它 | A collection belongs to one owner. Saving locks that collection before allocating item_no. The same video cannot occur twice in the same collection. |
| 3:10–3:45 | 新视频点 Hide，尝试新增评论观察拒绝，再 Publish again | Hiding retains existing interactions. New interactions take a shared lock on the video and must see PUBLISHED. Hiding needs a conflicting lock, so the order of operations is consistent under concurrency. |
| 3:45–4:30 | SQL reports 运行 Q03、Q04 或 Q08 | These reports execute our submitted SELECT statements. Zero like counts are retained with an outer join. The recursive comment result uses a redacted anchor for hidden parents. Dense rank preserves popularity ties. |
| 4:30–5:00 | 报告第 14、16 节总结 | We passed 31 structural probes, 21 business and concurrency tests, four immutability probes and 14 browser checks. The schema remains normalized. Our small EXPLAIN observation is not a production performance claim. |

如果网络变慢，少展示一个报表，保留实际写入、隐藏规则和测试总结。不要把保存的 JSON 伪装为当场数据库返回。

## 常见问题

**为什么仍是 10 个实体？** USER、VIDEO、MUSIC、TOPIC、COMMENT、VIDEO_TOPIC、VIDEO_LIKE、FOLLOW、COLLECTION、COLLECTION_ITEM。登录角色是数据库基础设施，不是新增业务表；Supabase 自带 auth/storage 也不是本模型实体。

**外键为什么不够？** 它能证明父评论存在，却不能单独证明父子属于同一视频或操作者拥有视频。触发器验证同视频和不可变性，私有函数核对真实登录身份和所有者。

**如何证明没有评论环？** 初始数据无环；新增节点只能引用已经存在的父节点，禁止自引用，之后不可改父链和身份。已有图因此不能被重新连接成环。

**如何处理两个收藏同时发生？** 先 FOR UPDATE 锁父收藏夹，再 MAX(item_no)+1。两个实际数据库连接测试得到了 1 和 2；不是先在网页里猜编号。

**为什么使用 SECURITY DEFINER？** 它是私有、有限操作网关，让受限登录角色不直接读写业务表。函数固定 search_path，表名全部限定，核实 SESSION_USER，并拒绝输入身份字段。它不是公开 RPC，也不声称 RLS 策略本身完成了身份授权。

**为什么没有额外存点赞数？** 当前规模下聚合查询足够，存计数会增加更新一致性成本。没有用一条小样本 EXPLAIN 推断需要反规范化。

**为什么原型账号固定？** 本项目验收重点是关系设计、SQL 和数据库事务。受控 LOGIN 角色提供真实可测试身份；开放注册、找回密码和生产认证明确不在范围内。

**如何复现？** 提交包有 schema、seed、业务 SQL、白名单报表、应用和测试。新建独立免费 Supabase 项目后运行 setup_demo.py，脚本拒绝覆盖已有 schema；密码不会随提交包传递。
