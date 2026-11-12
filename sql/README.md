# SQL 执行入口

2026-11-12 起，当前数据库为 Supabase / PostgreSQL 17.11。

**只执行 `postgresql/` 下的文件。**本目录根部的 `01_schema.sql` 和 `90_inspect_schema.sql` 是保留的 MySQL 历史版本，不能导入 Supabase。

| PostgreSQL 文件 | 用途 | 当前状态 |
| --- | --- | --- |
| 01_schema.sql | 创建 douyin schema、10 张表、索引与私有访问边界 | 已通过托管迁移执行一次 |
| 02_seed.sql | 最初 69 条固定虚构记录 | 历史初始种子；与最终快照二选一 |
| 02_final_snapshot.sql | 最终报告对应的精确 100 条虚构记录 | 已在独立回滚 schema 中重建验证 |
| 04_business_rules.sql | 可信登录身份、业务网关、锁与触发器 | 已部署并实测 |
| 05_report_interface.sql | 操作员的固定 SELECT 白名单 | 已部署并实测 |
| 06_guard_record_fix.sql | 共享触发器字段解析修复 | 已部署；重建时可重复替换函数 |
| 03_queries.sql | 报告中的 10 项 SELECT，含递归 CTE、窗口函数、聚合和外连接 | 已逐项执行并核对 |
| 90_inspect_schema.sql | 只读回读实际结构、权限与行数 | 已执行 |
| 95_constraint_tests.sql | 31 项结构正反例；每个探测在异常子事务中回滚 | 已执行通过 |
| 96_immutability_tests.sql | 自引用和身份/父链不可变的 4 项探测 | 已执行通过 |

初始化顺序为 01 → 02_final_snapshot（或 02_seed，二选一）→ 04 → 05 → 06。01 和两份 02 都不应在现有项目重复运行。02 遇到任何业务表已有数据会拒绝，不会清空或覆盖。03 和 90 可只读重跑；95 依赖原始固定种子数据，测试探测行会回滚。任何重置、删除或清空都需要另行批准。
