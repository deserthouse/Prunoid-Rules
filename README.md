<div align="center">

# Prunoid-Rules

供 [Prunoid](https://github.com/deserthouse/Prunoid) 识别 Android 应用内嵌 SDK 的规则库。每条规则记录来源、置信度和组件处置建议。

[订阅规则](#-订阅使用) · [核对数据来源](#-数据来源与协议) · [提交规则](CONTRIBUTING.md)

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE) [![Rules](https://img.shields.io/badge/Rules-2079-green.svg)](#-数据来源与协议) [![CI](https://img.shields.io/github/actions/workflow/status/deserthouse/Prunoid-Rules/ci.yml?style=flat-square)](https://github.com/deserthouse/Prunoid-Rules/actions)

</div>

---

## 🔗 订阅使用

Prunoid 可以同时使用内置快照和多个订阅源。同一 `id` 出现在多个源时，采用置信度较高的规则。复制下列一个地址添加到订阅。

**跟随 main**　订阅地址随官方规则更新。

```text
https://raw.githubusercontent.com/deserthouse/Prunoid-Rules/main/rules/snapshot.json
```

**固定版本（v14 tag，当前最新）**　需要复核同一批规则时使用这个地址。

```text
https://raw.githubusercontent.com/deserthouse/Prunoid-Rules/v14/rules/snapshot.json
```

历史 `vN` 地址继续有效。各版本的规则数见[更新日志](CHANGELOG.md)，自建源可沿用[快照结构](rules/snapshot.json)。

<details>
<summary>快照如何生成与复核</summary>

`aliases` 将跨语言的 SDK 别名映射到规范名。从 v13 起，`scripts/build_snapshot.py` 根据 `scripts/upstream_pins.json` 中的上游修订及 `--freeze-at` 时间戳生成快照。发布 tag 时，Linux CI 执行 `rebuild-check`，以 MD5 核对重建产物。v1 至 v12 保留历史产物。上游有仅大小写不同的文件名，Windows 本地构建可能少计 native 锚点。

</details>

## 📦 这是什么

面向 [Prunoid](https://github.com/deserthouse/Prunoid)（Android SDK 组件审计工具）的开放规则库：识别第三方 app 内嵌的广告 / 统计 / 推送 / 基础设施 SDK，并给出组件级的安全处置建议。

- **2,079 条** SDK 规则，每条携带 `sources[]`（数据出处）与 `confidence`（置信度），合并脚本可复现（数量随快照更新，CI 门禁保证本页与快照一致）
- **三路识别**：包名前缀 + 组件类名精确锚点 + 组件类名前缀（端侧确定性匹配，不猜测）
- **处置标注**：`safeToBlock` / `sideEffect` 逐条给出，不预测、不夸大
- **可选富字段**：`description` / `devTeam` / `sourceLink` / `iconUrl`（品牌图标 URL，贡献者以自有许可提供）——欢迎在 PR 中补全，App 端档案卡会直接呈现并署名 `contributors`

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

## AI 使用声明

本项目不含任何人类成分。AI 参与本仓维护文档的撰写，维护者负责审阅。规则数据按条目记录来源和社区贡献，继承署名见 [NOTICE](NOTICE)。

## ⚖️ 协议

Apache-2.0。继承数据的署名见 [NOTICE](NOTICE)。

---

<div align="center">

规则覆盖了你在乎的 SDK 吗？欢迎提 PR 补全 · ⭐ [Prunoid](https://github.com/deserthouse/Prunoid)

</div>
