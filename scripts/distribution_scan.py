# -*- coding: utf-8 -*-
"""
批GG-G3：分发频率巡检固化（2026-10-21，重建批K 流水线为可重跑脚本）

用途：输入一组第三方 APK（目录或设备直采），提取 manifest 组件类名，
     聚合"未被规则库覆盖的 Java 包前缀"，跨 app 出现 ≥N 次（默认 3）者
     报告为"通用 SDK 候选"。批K 先例：aapt 直读 manifest（防解析坑），自家包与
     平台前缀排除。

用法：
  python distribution_scan.py --apks <dir|file...> [--snapshot <snapshot.json>] [--min-apps 3]
  python distribution_scan.py --device <serial> [--max-apps 30] ...   # 设备直采模式

输出：stdout 报表（候选前缀/出现 app 数/样例 app）+ --json <path> 可选机读。
退出码：0 正常；2 输入为空。
纪律：只读分析，不安装不执行样本；z585/raybox 类"单 app 自有代码 R8 改名"
     不满足 ≥3 阈值自然落选，如出现在报表注释属正常证据留存。
"""
import argparse, json, os, re, subprocess, sys
from collections import defaultdict

# 平台/自家排除前缀（组件类名一级命名空间或完整前缀）
EXCLUDE_PREFIXES = [
    "android.", "androidx.", "com.google.android.", "com.google.", "java.", "javax.",
    "io.github.deserthouse.",  # 自家
    "kotlin.", "kotlinx.", "org.jetbrains.",
]
# 前缀聚合粒度：类名取前 k 段（com.x.y.Zz -> com.x.y）
AGG_SEGMENTS = 3
MIN_SEGMENTS = 2

AAPT_CANDIDATES = []


def find_aapt():
    for cand in AAPT_CANDIDATES:
        if os.path.isfile(cand):
            return cand
    return None


def component_classes(apk, aapt):
    """aapt dump xmltree 解析 manifest 四类组件的 android:name。批K 坑：行内引号贪婪，用正则锚定属性名。"""
    out = subprocess.run([aapt, "dump", "xmltree", apk, "AndroidManifest.xml"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        return None
    classes = set()
    cur = None
    name_re = re.compile(r'A: android:name\([^)]*\)="([^"]+)"')
    tag_re = re.compile(r"E: (activity|activity-alias|service|receiver|provider) \(line")
    for line in out.stdout.splitlines():
        m = tag_re.search(line)
        if m:
            cur = m.group(1)
            continue
        if cur and line.strip().startswith("A:"):
            m2 = name_re.search(line)
            if m2:
                classes.add((cur, m2.group(1)))
                cur = None
    return classes


def covered(cls, prefixes):
    low = cls.lower()
    for p in prefixes:
        if low.startswith(p.lower().rstrip(".")):
            return True
    return False


def load_prefixes(snapshot):
    snap = json.load(open(snapshot, encoding="utf-8"))
    prefixes = set()
    for s in snap["sdks"]:
        for p in s.get("packPrefixes", []):
            prefixes.add(p.rstrip("."))
        for c in s.get("components", []):
            prefixes.add(c["class"])  # 锚点组件按全类名精确覆盖
    return snap, prefixes


def agg_prefix(cls):
    seg = cls.split(".")
    k = min(AGG_SEGMENTS, len(seg) - 1)
    k = max(k, MIN_SEGMENTS)
    return ".".join(seg[:k])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apks", nargs="*", help="APK 文件或目录")
    ap.add_argument("--device", help="设备直采模式：adb serial")
    ap.add_argument("--max-apps", type=int, default=30, help="设备直采上限")
    ap.add_argument("--snapshot", default=os.path.join(os.path.dirname(__file__), "..", "rules", "snapshot.json"))
    ap.add_argument("--min-apps", type=int, default=3)
    ap.add_argument("--dump-all", action="store_true", help="输出全量未匹配前缀聚合（巡检报表，不限阈值）")
    ap.add_argument("--json", help="机读输出路径")
    args = ap.parse_args()

    aapt = find_aapt()
    if not aapt:
        print("aapt not found; set AAPT_CANDIDATES or PATH", file=sys.stderr)
        sys.exit(2)

    apks = []  # (label, path)
    if args.device:
        adb = os.environ.get("ADB", "adb")
        out = subprocess.run([adb, "-s", args.device, "shell", "pm", "list", "packages", "-3"],
                             capture_output=True, text=True).stdout
        pkgs = [l.split(":", 1)[1].strip() for l in out.splitlines() if l.startswith("package:")]
        for pkg in pkgs[: args.max_apps]:
            path = subprocess.run([adb, "-s", args.device, "shell", "pm", "path", pkg],
                                  capture_output=True, text=True).stdout
            m = re.search(r"package:(\S+\.apk)", path)
            if not m:
                continue
            local = os.path.join(os.environ.get("TEMP", "."), f"scan_{pkg}.apk")
            if not os.path.isfile(local) or os.path.getsize(local) == 0:
                r = subprocess.run([adb, "-s", args.device, "pull", m.group(1), local],
                                   capture_output=True, text=True)
                if r.returncode != 0:
                    continue
            apks.append((pkg, local))
    else:
        for p in args.apks or []:
            if os.path.isdir(p):
                apks.extend((f[:-4], os.path.join(p, f)) for f in sorted(os.listdir(p)) if f.endswith(".apk"))
            elif os.path.isfile(p):
                apks.append((os.path.basename(p)[:-4], p))

    if not apks:
        print("no APK input", file=sys.stderr)
        sys.exit(2)

    snap, prefixes = load_prefixes(args.snapshot)
    print(f"snapshot: {len(snap['sdks'])} entities, {len(prefixes)} prefixes/anchors; apks: {len(apks)}")

    per_app_unmatched = {}
    agg = defaultdict(set)  # agg_prefix -> set(label)
    for label, path in apks:
        classes = component_classes(path, aapt)
        if classes is None:
            print(f"  [skip] {label}: aapt failed")
            continue
        unmatched = set()
        for _, cls in classes:
            if any(cls.startswith(e) for e in EXCLUDE_PREFIXES):
                continue
            if covered(cls, prefixes):
                continue
            unmatched.add(cls)
            agg[agg_prefix(cls)].add(label)
        per_app_unmatched[label] = len(unmatched)
        print(f"  {label}: {len(classes)} components, {len(unmatched)} unmatched")

    candidates = sorted(
        ((p, apps) for p, apps in agg.items() if len(apps) >= args.min_apps
         and not any(p.startswith(e) for e in EXCLUDE_PREFIXES)),
        key=lambda x: (-len(x[1]), x[0]),
    )
    print(f"\n== candidates (>= {args.min_apps} apps, top-level {AGG_SEGMENTS} segments) ==")
    for p, apps in candidates:
        print(f"  {p}  [{len(apps)} apps]  e.g. {', '.join(sorted(apps)[:3])}")
    print(f"total candidates: {len(candidates)}")

    if args.dump_all:
        print("\n== all unmatched prefixes (desc) ==")
        for p, apps in sorted(agg.items(), key=lambda x: -len(x[1]))[:40]:
            print(f"  {len(apps)}  {p}   e.g. {', '.join(sorted(apps)[:3])}")

    if args.json:
        json.dump({
            "apks": {k: v for k, v in per_app_unmatched.items()},
            "candidates": [{"prefix": p, "apps": sorted(a)} for p, a in candidates],
            "allPrefixes": [{"prefix": p, "appCount": len(a), "apps": sorted(a)} for p, a in sorted(agg.items(), key=lambda x: -len(x[1]))],
            "snapshotEntities": len(snap["sdks"]),
        }, open(args.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"json -> {args.json}")


if __name__ == "__main__":
    AAPT_CANDIDATES = [
        r"C:\Users\deser\Android\Sdk\build-tools\37.0.0\aapt.exe",
    ]
    import glob as _g
    AAPT_CANDIDATES += sorted(_g.glob(r"C:\Users\deser\Android\Sdk\build-tools/*/aapt.exe"), reverse=True)
    main()
