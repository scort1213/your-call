#!/usr/bin/env python3
"""从判断卡生成"一页纸"（三家 Agent 每次开工读的那一页）。
用法：一页纸.py                 正式版：只收"已确认"且分数 ≥0 的卡；一张都没有就拒绝（除非加 --allow-empty）
      一页纸.py --preview       预览版：另外收"候选"里独立一手证据 ≥2 的卡（标明未生效，不能发布）
只收范围是"通用"的卡；只适用于某个领域（例如"生图"）的卡留在库里，不进全局一页纸。
超过字符上限时报错，不写文件，旧的一页纸保持不变。"""
import sys, datetime
from lib import conf, load, atomic_write, GROUPS

HEAD = {
    "关键节点": "## 这些情况必须停下来问我",
    "问法": "## 怎么问我",
    "取舍": "## 两样冲突时我选哪边",
    "目标": "## 长期目标",
}


def main():
    c = conf()
    lib, preview = c["判断库"], "--preview" in sys.argv
    picked = {g: [] for g in GROUPS}
    for f, meta, _, fl, _ in load(lib):
        confirmed = meta.get("状态") == "已确认" and int(meta.get("分数", 0)) >= 0
        candidate = preview and meta.get("状态") == "候选" and int(meta.get("一手证据", 0)) >= 2
        scope = meta.get("范围", "通用").split("（")[0]
        if not (confirmed or candidate) or scope != "通用":
            continue  # 只适用于某个领域的卡不进全局一页纸
        line = f"- 当{fl['当']}：{fl['选']}；不要{fl['而不是']}。（{meta['编号']}）"
        picked[meta.get("类别", "取舍")].append(line)
    total = sum(map(len, picked.values()))
    if total == 0 and not preview and "--allow-empty" not in sys.argv:
        sys.exit("没有已确认的卡，不生成正式一页纸（旧文件保持不变）。确实要清空，加 --allow-empty。")
    stamp = datetime.date.today().isoformat()
    out = [f"<!-- 一页纸：{'预览' if preview else '正式'}，{total} 条 -->", "# 我的判断（一页纸）", ""]
    if preview:
        out += ["> **预览版，尚未生效**：含未经我确认的候选，不会发布。", ""]
    out += [f"> 生成于 {stamp}，来自判断库的「判断卡」。这页没覆盖的情况、或两条判断互相冲突时，停下来问我。",
            "> 按这页做决定时，在回复里注明依据的编号（例如\"按 J-05\"）。", ""]
    for g in GROUPS:
        if picked[g]:
            out += [HEAD[g], *picked[g], ""]
    text = "\n".join(out)
    if len(text) > c["一页纸上限字符"]:
        sys.exit(f"一页纸会有 {len(text)} 个字符，超过上限 {c['一页纸上限字符']}：先合并或移出几条。旧文件保持不变。")
    atomic_write(lib / "一页纸.md", text)
    print(f"一页纸：{total} 条，{len(text)} 个字符（上限 {c['一页纸上限字符']}）{'，预览版' if preview else '，正式版'}")


if __name__ == "__main__":
    main()
