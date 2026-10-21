# Changelog — Prunoid-Rules

数据版本随快照更新打 `vN` tag，固定 URL 内容永不变更。规则数为该版快照 `sdks` 条目数（本表由 `git show vN:rules/snapshot.json` 逐版实算）。

| 版本 | 规则数 | 主要变化 |
|---|---|---|
| v13 | 2,074 | 可重建性归一（批K）：构建脚本整体公开（参数化输入+--freeze-at 确定性+glob 排序），上游输入固定点入 scripts/upstream_pins.json（LCR 51eb734/blocker b30c5d6c/oF2pks 0d97bff5），CI 新增 tag 冻结重建 byte 级门禁（rebuild-check）。规则数据与 v12 语义全等（实体集/组件集/sources 标签零差异；3 个多组件实体的富描述因确定性排序选取同源等价描述），generator 字段改仓内标识；官方构建环境=Linux CI（上游 libMuPDF/libmupdf 大小写碰撞文件在 Windows 检出缺一，v13 首打时 Windows 产物少 1 条 MuPDF native 锚点，已以 CI 重建产物更正并重打 tag） |
| v12 | 2,074 | 批GG 发货名情报常态化：网迈（lywm，OOPZ manifest 实证）补录、百度 mobads 系两对别名合并、byted.live.lite 归位 Douyin Live Lite、分发频率巡检脚本固化（distribution_scan.py）、PTG 第二命名空间（com.ptg.adsdk）并入 |
| v11 | 2,073 | 上游同调：LibChecker-Rules c54757b→51eb734，Bundle v4→v5 |
| v8–v10 | 2,003 | 数据批次收尾与长尾清洗：独占域对提取合并、backlog 全量裁决、GAME_CATEGORY_MAP 显式归类（细节见各 tag 提交记录） |
| v6–v7 | 2,003 | 手机吧 352 应用大样本扩充、Pangle 同名直系与过宽前缀判定 |
| v3–v5 | 1,951→1,969 | 分类关键词表扩充、联网判决、批量样本扩充 |
| v1–v2 | 1,929 | 首个快照（schemaVersion 1）与分类关键词表 |
