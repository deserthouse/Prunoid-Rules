# -*- coding: utf-8 -*-
"""规则快照校验：schema/枚举/id 唯一性/sources 必填/名称与前缀无首尾空白。CI 与本地共用。"""
import json, sys, re

CATEGORIES = {"ads","push","analytics","quality","social_or_pay","maps","infra","security","framework","other"}
CONF = {"high","medium","low"}
TYPES = {"activity","service","receiver","provider","native"}

def main(path):
    errs = []
    d = json.load(open(path, encoding="utf-8"))
    if "schemaVersion" not in d: errs.append("missing schemaVersion")
    sdks = d.get("sdks", [])
    if not sdks: errs.append("sdks empty")
    seen = {}
    name_count = {}
    for i, r in enumerate(sdks):
        nm = r.get("name", "")
        if nm: name_count[nm] = name_count.get(nm, 0) + 1
        rid = r.get("id")
        if not rid: errs.append(f"[{i}] missing id"); continue
        if rid in seen: errs.append(f"[{i}] duplicate id {rid} (first at [{seen[rid]}])")
        seen[rid] = i
        if not r.get("name"): errs.append(f"[{rid}] missing name")
        if not r.get("sources"): errs.append(f"[{rid}] sources empty (来源必填)")
        if r.get("category") not in CATEGORIES: errs.append(f"[{rid}] bad category {r.get('category')}")
        if r.get("confidence") not in CONF: errs.append(f"[{rid}] bad confidence {r.get('confidence')}")
        if not isinstance(r.get("safeToBlock"), bool): errs.append(f"[{rid}] safeToBlock not bool")
        # v15：名称/前缀/描述不得有首尾空白或控制字符——上游标签曾带前导空格
        # （" 人脸核身 SDK"），别名表因此匹配不上，实体一直没并入规范名
        if nm != nm.strip() or "  " in nm or re.search(r"[\u3000\x00-\x1f]", nm):
            errs.append(f"[{rid}] name has stray whitespace: {nm!r}")
        for pfx in r.get("packPrefixes", []):
            if not isinstance(pfx, str) or not pfx or pfx != pfx.strip() or " " in pfx:
                errs.append(f"[{rid}] bad packPrefix {pfx!r}")
        desc = r.get("description", "")
        if not isinstance(desc, str) or desc != desc.strip():
            errs.append(f"[{rid}] description has stray whitespace")
        for c in r.get("components", []):
            if c.get("type") not in TYPES: errs.append(f"[{rid}] bad component type {c.get('type')}")
            if not c.get("class"): errs.append(f"[{rid}] component missing class")
    # 同名重复：警告级（v2 原则 §1.2——多源对同一 SDK 各持一条是合法形态，合并靠 build_snapshot）
    warns = []
    for n, c in name_count.items():
        if c > 1:
            warns.append(f"duplicate rule name x{c} (legal multi-source form): {n}")
    # §4.3 前缀一致性：不同规则的前缀前两段相同 -> 潜在误归类/应拆分（警告级）
    two_seg_owner = {}
    for r in sdks:
        for pfx in r.get("packPrefixes", []):
            two = ".".join(pfx.strip(".").split(".")[:2])
            if two.count(".") < 1 or len(two) < 3:
                continue
            prev = two_seg_owner.get(two)
            if prev and prev[1] != r.get("name"):
                warns.append(f"prefix family collision on '{two}.*': {prev[0]} vs {r.get('name')}")
            elif not prev:
                two_seg_owner[two] = (r["id"], r.get("name"))
    for w in warns[:30]:
        print("WARN:", w)
    if warns:
        print(f"({len(warns)} warnings total)")
    if errs:
        print("INVALID:")
        for e in errs[:50]: print(" -", e)
        sys.exit(1)
    print(f"OK: {len(sdks)} rules valid ({path})")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "rules/snapshot.json")
