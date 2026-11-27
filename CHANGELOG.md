# Changelog — Prunoid-Rules

数据版本随快照更新打 `vN` tag，固定 URL 内容永不变更。规则数为该版快照 `sdks` 条目数（本表由 `git show vN:rules/snapshot.json` 逐版实算）。

| 版本 | 规则数 | 主要变化 |
|---|---|---|
| v16 | 2,121 | 上游同步：LibChecker-Rules 51eb734→7815d0c（+2 条组件锚点：Jetpack AppFunctions 的 1 个 receiver、Jetpack Room 的 1 个 service；+3 条 native 锚点：libxml2、libleveldbjni、libhrt_core；上游把 libMuPDF.so 的条目移入 regex/ 子目录——该子目录本库一直不取，MuPDF 的 native 锚点少 1 条，大小写碰撞随之消除）、blocker-general-rules 55ae4b9→312d42b（+39 条规则、12 条既有规则补 16 个包名前缀；“可安全禁用”标注零翻转）。数据卫生：24 个新实体显式归类（境外营销/推送类平台）、40 条项目自撰补充描述、来源标签去掉过时的“v44”；两项前缀裁决（穿山甲剔除 com.byted.live.、DataFinder 剔除 com.volcengine.onekit.）与一对别名（BIGO Ads→Bigo Ads），判定书 docs/alias_decisions.md K 节。构建脚本：glob 排序把路径分隔符归一为 /——此前按原生路径串排序，Windows 本地构建与 Linux CI 产物有两条相邻实体顺序互换（内容逐字段一致），v16 固定点下两者逐字节一致。来源说明：blocker-general-rules 的规则现由 blocker-catalog 生成 |
| v15 | 2,079 | 数据卫生批：①归类正则中的短缩写记号（BLE/IM/FIR/RTC 等）改为大小写敏感整词，修正 27 个名称共 50 条目的误归类（AdTiming 与阿里妈妈原 AdsMogo→广告；Firebase 云消息→框架、Firebase 认证→账号支付；Google DoubleClick→广告；Estimote/Gimbal 等信标→地图），另为样本应用命中的 9 个条目补显式归类；②名称去首尾空白（" 人脸核身 SDK" 归位后并入腾讯云慧眼的既有别名）；③新增项目自撰补充描述 450 个名称（941 条目），无描述的规范组 500→77，其中高置信/带组件/标注可禁用的组 429→22；④新增 3 对前缀同域别名（Tencent Advertising→腾讯广告 SDK、UBiX Ads→Ubix SSP、Octopus Ad→Octopus Ads），判定书见 docs/alias_decisions.md J 节；⑤校验器新增名称/前缀/描述空白硬校验。规则数不变，上游固定点不变 |
| v14 | 2,079 | 上游同步：blocker-general-rules b30c5d6c→55ae4b9（Exodus 同步新增 ACRA/Backtrace/Sentry/月颖崩溃 SDK 四实体+UBiX Ads/Octopus Ads 组件锚点+Meizu Ads 前缀增补+贡献者更新；networkSignature 字段不入快照——管线仅消费六字段，ODbL 红线无接触；SAP CDC (Gigya) 更名 Gigya，运行时经既有别名合并） |
| v13 | 2,074 | 可重建性归一（批K）：构建脚本整体公开（参数化输入+--freeze-at 确定性+glob 排序），上游输入固定点入 scripts/upstream_pins.json（LCR 51eb734/blocker b30c5d6c/oF2pks 0d97bff5），CI 新增 tag 冻结重建 byte 级门禁（rebuild-check）。规则数据与 v12 语义全等（实体集/组件集/sources 标签零差异；3 个多组件实体的富描述因确定性排序选取同源等价描述），generator 字段改仓内标识；官方构建环境=Linux CI（上游 libMuPDF/libmupdf 大小写碰撞文件在 Windows 检出缺一，v13 首打时 Windows 产物少 1 条 MuPDF native 锚点，已以 CI 重建产物更正并重打 tag） |
| v12 | 2,074 | 批GG 发货名情报常态化：网迈（lywm，OOPZ manifest 实证）补录、百度 mobads 系两对别名合并、byted.live.lite 归位 Douyin Live Lite、分发频率巡检脚本固化（distribution_scan.py）、PTG 第二命名空间（com.ptg.adsdk）并入 |
| v11 | 2,073 | 上游同调：LibChecker-Rules c54757b→51eb734，Bundle v4→v5 |
| v8–v10 | 2,003 | 数据批次收尾与长尾清洗：独占域对提取合并、backlog 全量裁决、GAME_CATEGORY_MAP 显式归类（细节见各 tag 提交记录） |
| v6–v7 | 2,003 | 手机吧 352 应用大样本扩充、Pangle 同名直系与过宽前缀判定 |
| v3–v5 | 1,951→1,969 | 分类关键词表扩充、联网判决、批量样本扩充 |
| v1–v2 | 1,929 | 首个快照（schemaVersion 1）与分类关键词表 |
