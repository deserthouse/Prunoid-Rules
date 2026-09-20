# 贡献指南

## 提交什么

- 新 SDK 规则（新 `id`）
- 既有规则修正（更准确的包名前缀 / 组件锚点 / safeToBlock / sideEffect）
- 分类修正（category）

## 规则格式

修改 `rules/snapshot.json`（或提交独立分片由维护者合并），单条结构：

```json
{
  "id": "12位十六进制或语义化短id",
  "name": "SDK 名称（中英文皆可）",
  "company": "厂商",
  "category": "ads|push|analytics|quality|social_or_pay|maps|infra|security|framework|other",
  "packPrefixes": ["com.example.sdk."],
  "components": [
    {"type": "activity|service|receiver|provider|native", "class": "com.example.sdk.AdActivity"}
  ],
  "safeToBlock": false,
  "sideEffect": "禁用后的已知影响（没有依据就留空）",
  "sources": ["你的数据出处"],
  "confidence": "high|medium|low",
  "contributors": ["你的ID"]
}
```

## 硬性要求

1. **sources 必填**：说明数据从哪来（实机分析 / 公开文档 / dex 逆向 / 上游仓库）。
   无法说明出处的规则会被拒绝。
2. **不复制文案**：描述性文字请自行撰写；不要从其他项目拷贝 description。
3. **safeToBlock 要有依据**：true 意味着"禁用不影响 app 核心功能"，
   请在 sideEffect 或 PR 描述里说明验证方式。
4. **不收录系统/框架组件的禁用建议**：本库只面向第三方 SDK。

## CI 校验

PR 会自动运行 `scripts/validate_rules.py`：
- JSON 可解析、schemaVersion 存在
- 每条 id 唯一、sources 非空、confidence/safety 枚举合法
- 组件 type 枚举合法

本地校验：`python scripts/validate_rules.py rules/snapshot.json`

## 最简单的方式：提交组件清单（无需写代码，2026-09-21 起）

1. 安装 [Prunoid](https://github.com/deserthouse/Prunoid) 扫描设备
2. 任一应用详情 → 「未识别组件」→ 展开 → 底部「分享组件清单」
3. 用 **Component report** issue 模板粘贴导出的 JSON
4. 维护者研判后收录（下个快照生效）；清单仅含包名与类名（客观事实），无个人信息

## 数据治理原则（2026-09-19 起，v2）

收录四步：事实提取（manifest 组件）→ 研判（附公开依据）→ schema 化（source 标注+confidence）→ CI 门禁。
安全等级只升不造；研判不确定项宁缺毋滥。详见主仓 research/《数据管理原则 v2》。
