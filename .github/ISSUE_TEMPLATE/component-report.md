name: 组件清单提交（Component report）
about: 从 Prunoid app「分享组件清单」导出的 JSON 贴到这里，供规则研判收录
title: "[report] "
labels: component-report
body:
  - type: markdown
    attributes:
      value: |
        感谢贡献！在 app 详情页 → 未识别组件 → 「分享组件清单」，把导出的 JSON 粘贴到下方。
        清单只包含包名与组件类名（客观事实），不含任何个人信息。
        Only package names and component class names are included (objective facts); no personal data.
  - type: textarea
    id: json
    attributes:
      label: 组件清单 JSON
      description: 粘贴 app 内导出的完整 JSON
      render: json
    validations:
      required: true
  - type: textarea
    attributes:
      label: 备注（可选）
      description: 你对某个 SDK 的了解（厂商/用途/禁用副作用），或希望优先研判的前缀
