<div align="center">

# Prunoid-Rules

**Prunoid 的 SDK 识别与安全禁用规则库 —— 开放、可溯源、社区共建**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Rules](https://img.shields.io/badge/Rules-1929-green.svg)](#-数据来源与协议)
[![CI](https://img.shields.io/github/actions/workflow/status/deserthouse/Prunoid-Rules/ci.yml?style=flat-square)](https://github.com/deserthouse/Prunoid-Rules/actions)

主项目：[Prunoid](https://github.com/deserthouse/Prunoid) · 贡献指南：[CONTRIBUTING.md](CONTRIBUTING.md)

</div>

---

## 📦 这是什么

面向 [Prunoid](https://github.com/deserthouse/Prunoid)（Android SDK 组件审计工具）的开放规则库：识别第三方 app 内嵌的广告 / 统计 / 推送 / 基础设施 SDK，并给出组件级的安全处置建议。

- **1,929 条** SDK 规则，每条携带 `sources[]`（数据出处）与 `confidence`（置信度），合并脚本可复现
- **三路识别**：包名前缀 + 组件类名精确锚点 + 组件类名前缀（端侧确定性匹配，不猜测）
- **处置标注**：`safeToBlock` / `sideEffect` 逐条给出，不预测、不夸大
- **可选富字段**：`description` / `devTeam` / `sourceLink` / `iconUrl`（品牌图标 URL，贡献者以自有许可提供）——欢迎在 PR 中补全，App 端档案卡会直接呈现并署名 `contributors`

## 🔗 订阅使用

Prunoid App 支持「内置快照 + 多源订阅」：可同时订阅多个规则源并发生效（同 `id` 冲突时**置信度高者胜**），官方源如下——

- **跟随最新 main**：`https://raw.githubusercontent.com/deserthouse/Prunoid-Rules/main/rules/snapshot.json`
- **固定版本（v1 tag）**：`https://raw.githubusercontent.com/deserthouse/Prunoid-Rules/v1/rules/snapshot.json`

版本策略：快照更新打 `vN` tag，固定 URL 内容永不变更。自建源只要符合[同一 schema](rules/snapshot.json) 即可被订阅。

## 🧪 质量门禁（CI）

每个 PR 自动执行 [`scripts/validate_rules.py`](scripts/validate_rules.py)：

- **硬错误**（阻断合并）：schema 校验、`id` 重复、`sources` 为空、枚举字段非法
- **警告**（不阻断）：同名重复规则（多源对同一 SDK 各持一条属合法形态，但会造成图标/描述映射歧义，提示去重）

## 📊 数据来源与协议

| 来源 | 协议 | 用法 |
|---|---|---|
| [LibChecker-Rules](https://github.com/LibChecker/LibChecker-Rules) | Apache-2.0 | 组件识别锚点（1,133 组件 + 1,406 native） |
| [blocker-general-rules](https://github.com/lihenggui/blocker-general-rules) | Apache-2.0 | SDK 禁用规则（468 条，含 safeToBlock/sideEffect） |
| oF2pks / 3xodusprivacy-toolbox | 无声明（仅事实字段） | 包名前缀补充（619 条，低置信度标注） |
| Fuck.AD dex 提取 | 客观事实 | 聚合广告 SDK 根包名（16 家） |
| 实机 APK 分析 | 一手数据 | 置信度最高 |

明确不使用：DuckDuckGo tracker-blocklists（CC BY-NC-SA 禁商用）、AppManager 数据文件（GPL）、Exodus 数据库直接合并（ODbL 同源义务）。逐源许可判定原则见 [CONTRIBUTING](CONTRIBUTING.md)。

## 🤝 贡献

见 [CONTRIBUTING.md](CONTRIBUTING.md)。要点：数据来源必填（说不清出处的规则会被拒绝）、`safeToBlock: true` 必须附验证依据、描述文案自行撰写（不要从其他项目复制）。

## ⚖️ 协议

Apache-2.0。继承数据的署名见 [NOTICE](NOTICE)。

---

<div align="center">

规则覆盖了你在乎的 SDK 吗？欢迎提 PR 补全 · ⭐ [Prunoid](https://github.com/deserthouse/Prunoid)

</div>
