#!/usr/bin/env python3
"""README 与快照一致性门禁（审计 PRUNOID-RULES-02）。

校验：README 徽章与正文中的规则数 == len(snapshot.sdks) == stats.sdks；
README 的"固定版本（vN tag，当前最新）"指向 git 最高 tag。
更新快照而不同步 README 时，本脚本非零退出阻断 CI。
"""
import json
import re
import subprocess
import sys

snap = json.load(open("rules/snapshot.json", encoding="utf-8"))
n = len(snap["sdks"])
stats = snap.get("stats", {}).get("sdks")
if stats is not None and stats != n:
    sys.exit(f"FAIL: stats.sdks={stats} != len(sdks)={n}")

readme = open("README.md", encoding="utf-8").read()
for pat, desc in [
    (r"Rules-(\d+)-green", "badge count"),
    (r"(\d[\d,]*)\s*条\*?\*?\s*SDK 规则", "body count"),
]:
    hits = re.findall(pat, readme)
    if not hits:
        sys.exit(f"FAIL: README 中未找到{desc}锚点，请同步锚点或更新本脚本")
    for c in hits:
        c = c.replace(",", "")
        if c != str(n):
            sys.exit(f"FAIL: README {desc} {c} != snapshot {n}")

latest = subprocess.run(
    "git describe --tags --abbrev=0", shell=True, capture_output=True, text=True
).stdout.strip()
m = re.search(r"固定版本（v(\d+) tag，当前最新）", readme)
if not m:
    sys.exit("FAIL: README 未找到『固定版本（vN tag，当前最新）』锚点")
if f"v{m.group(1)}" != latest:
    sys.exit(f"FAIL: README 最新固定版本 v{m.group(1)} != 最高 tag {latest}")
if f"/{latest}/rules/snapshot.json" not in readme:
    sys.exit(f"FAIL: README 固定版本 URL 未指向 {latest}")

print(f"README sync PASS: {n} rules, latest tag {latest}")
