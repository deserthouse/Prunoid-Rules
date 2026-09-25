# 别名合并判定书（批 H1/H2，2026-09-26）

> 判定人：AI（用户指令转授）。方法：命名空间锚点机器证据（ns3 双向匹配）+ 组件锚点并集比对 + 联网官方佐证。
> 纪律：保守合并——safeToBlock=AND、confidence 取低、锚点并集（合并只增不减，识别命中率构造性不降）。
> 撤销路径：删 ALIAS_MERGES 对应条目 + 重新生成快照即回滚。

## A. 合并（14 对 → 12 个 canonical）

| # | 别名 → 规范名 | 级别 | 证据 |
|---|---|---|---|
| 1 | Pangle 穿山甲 → Pangle SDK | B | 同 SDK 双区域品牌，共享 `com.bytedance.sdk.openadsdk` 命名空间（TopOn 集成文档：国内=CSJ/穿山甲、海外=Pangle，同引擎） |
| 2 | Pangolin Advertising SDK → Pangle SDK | A | ns3 重叠 0.75（shared=6/8）：`com.bytedance.pangle.`/`openadsdk` 等全同族；Pangolin=Pangle 旧国际名 |
| 3 | AppLovin → AppLovin MAX | B | 官方：MAX 即当前 AppLovin SDK（v11 MoPub 并入），同一 `com.applovin` 包，Exodus/MobSF 单实体收录 |
| 4 | Huawei Ads SDK → HUAWEI Ads Kit | B | 官方 keep 规则：Ads Kit 混淆豁免含 `com.huawei.openalliance.ad.**`（=Huawei Ads SDK 实体的全部锚点） |
| 5 | Jetpack Camera2 → Jetpack Camera | B | `androidx.camera:camera-camera2` 是 CameraX 的实现后端 artifact，同库族（core/camera2.impl 同 ns2 `androidx.camera`） |
| 6 | Ali Mobile push → 阿里移动推送 | A | ns3 全等 1.00（4/4），双语名 |
| 7 | Tencent Mobile Push → 腾讯移动推送 | A | ns3 全等 1.00，双语名 |
| 8 | Unity3d Ads → Unity Ads | A | ns3 全等 1.00（`com.unity3d.ads`），拼写变体 |
| 9 | Liftoff Monetize → Vungle | B | Liftoff 收购 Vungle 后更名；实体锚点就是 `com.vungle.ads/warren`（包名未变） |
| 10 | Google CrashLytics → Google Crashlytics | A | 同名大小写拼写变体（L 大写错误） |
| 11 | Android Beacon Library → AltBeacon | A | 同一开源项目两名（altbeacon.org = Android Beacon Library），ns3 全等 |
| 12 | Google Ads → Google AdMob | B | 两实体锚点同属 Google Mobile Ads SDK（`com.google.android.gms.ads.*` 全族 + firebase_ads/com.google.ads 变体），AdMob=该 SDK 的产品名 |
| 13 | Oppo Advertising Alliance → OPPO 广告 SDK | A | Alliance 前缀 `com.opos.cmn./com.opos.mobad.` 完全包住 广告 SDK 实体的组件命名空间（0.67 重叠=子集关系） |
| 14 | HMS Core Library → HMS Core | A | Library 实体前缀集是 Core 实体前缀集的纯子集（5 前缀全在 Core 内），同产品两名 |

## B. 保持独立（含理由）

### A 层 20 对中排除的 16 对
- Agora RTC SDK ↔ RTC2：两代共存（`io.agora.rtc`/`io.agora.rtc2`），独立 artifact，可同 app 并存
- mPaaS ↔ 扫一扫/社交分享：平台 vs 平台功能模块（独立 maven artifact）
- Expo AV ↔ Framework：Expo 独立模块
- Fcitx 5 ↔ Fcitx 5 Lua：输入法 vs Lua 插件
- Google Play Core ↔ Play Services：不同产品（应用内更新 vs GMS 框架）
- Jetpack Media ↔ Media3：新旧两代并存（`androidx.media` vs `androidx.media3`）
- AGC ↔ AGC APM：平台 vs 性能监控模块
- HMS Core ↔ HMS Core AAID：集成桥 vs 广告标识服务（不同服务）
- HUAWEI CaaS Engine ↔ Ads Kit/Ads SDK/Push：不同产品（内容即服务 vs 广告 vs 推送）
- HUAWEI Ads Kit ↔ Huawei DTM、Ads SDK ↔ DTM、DTM ↔ Push：广告/标签管理/推送各自独立
- OPPO Push ↔ OPPO 广告 SDK：推送 vs 广告
- Unity Ads ↔ Unity Mono：广告 vs 引擎脚本运行时（每款 Unity 游戏都有 Mono，与广告无关）
- Unity Mono ↔ Unity Services Ads：同上反向

### H2 全库扫描中排除的 1 对
- Alipay Mobile SDK ↔ mPaaS（ns3 重叠 1.00）：命名空间同源（mPaaS 即支付宝 App 框架外发），但产品语义不同（支付 SDK vs 开发平台）——支付类组件禁用后果重，合并会让"禁用 mPaaS 容器"连带显示为"禁用支付宝支付"，语义污染大于去重收益。上游分立收录维持。

## C. 机器证据方法

- ns3 = 前缀/组件全类名的前三段命名空间；重叠度 = 交集/min(两侧)
- A 级 = 机器证据可独立定案；B 级 = 机器证据 + 官方文档联网佐证
- 全库扫描口径：跨名 ns3 重叠 ≥0.5 且 shared≥2（1338 名 → 11 对候选，14 判合并中 8 对来自此扫描）

## D. 生效与回归

- ALIAS_MERGES 增补 14 条（双侧脚本同步：主仓 `research/build_snapshot.py` 补 aliases 输出段 + 规则仓存档副本）
- 快照外科补丁：aliases 字段 + stats，实体集 2003 不动（别名合并=运行时语义，RuleDedup 消费）
- 证明：RuleDedup 合并为锚点并集——每个被合并实体的锚点全部保留，识别命中只增不减（构造性成立）
- 随版：规则仓 v7；主仓 app assets 同步（随下个 app 版本出包）

## E. 附：合并暴露的分类清洗（2026-09-26 同批）

primary 模拟（RuleDedup 口径：置信度→锚点数定主条目，category 随 primary）暴露 4 名实体预存错类，随批清洗：
- Liftoff Monetize：other → **ads**（categorize regex 缺 "Monetize"，曾致其夺 Vungle 组 primary 后把广告 SDK 踢出 Ads 类——合并模拟实抓）
- HUAWEI Ads Kit：other → **ads**（regex 缺 "Ads Kit"）
- Huawei Mobile Services (HMS) Core / Core Library：other → **framework**（共 10 实体；regex 缺 "HMS Core"，HMS Push 被更早的 push 组截获不受影响）
- 脚本侧 CAT_RULES 同步增补（两侧），快照外科补丁 11 实体；复跑 primary 模拟全组 category 归位
