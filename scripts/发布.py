#!/usr/bin/env python3
"""把一页纸写进三家 Agent 的全局规则文件（标记块之间，块外的内容不动）。
用法：发布.py                   演示：检查并显示会改什么，不写任何文件
      发布.py --apply           真写：先把原文件备份到 判断库/_发布备份/<时间>/，再写入
      发布.py --apply --allow-empty   允许发布 0 条的一页纸（会清空各目标里的判断块）
发布前全部检查通过才写：一页纸必须是正式版、不超过字符上限、不是 0 条；每个目标的标记块要么没有，要么开始、结束各一个且顺序对。
任何一个目标有问题，所有目标都不写。"""
import sys, difflib, datetime, shutil
from pathlib import Path
from lib import conf, atomic_write, PAGE_MARK

START, END = "<!-- 个人判断库：开始（由 /judgment 生成，别手改） -->", "<!-- 个人判断库：结束 -->"
START_KEY = "<!-- 个人判断库：开始"


def merged(old, page):
    """返回 (新内容, 问题)。"""
    block = f"{START}\n{page.strip()}\n{END}\n"
    s, e = old.count(START_KEY), old.count(END)
    if s == 0 and e == 0:
        return (old.rstrip("\n") + "\n\n" if old.strip() else "") + block, None
    if s == 1 and e == 1 and old.index(START_KEY) < old.index(END):
        a, rest = old.split(START_KEY, 1)
        return a + block + rest.split(END, 1)[1].lstrip("\n"), None
    return None, f"标记块残缺或重复（开始 {s} 个、结束 {e} 个），请先手动修好这个文件"


def main():
    c = conf()
    lib, apply, allow_empty = c["判断库"], "--apply" in sys.argv, "--allow-empty" in sys.argv
    page = (lib / "一页纸.md").read_text(encoding="utf-8")
    m = PAGE_MARK.match(page)
    errors = []
    if not m:
        errors.append("一页纸没有生成标记：请用 一页纸.py 重新生成，不要手改")
    elif m["kind"] != "正式":
        errors.append("一页纸是预览版：先在候选箱里确认，再运行 一页纸.py 生成正式版")
    elif m["n"] == "0" and not allow_empty:
        errors.append("一页纸是 0 条：发布会清空各目标里的判断块；确实要这样，加 --allow-empty")
    if len(page) > c["一页纸上限字符"]:
        errors.append(f"一页纸有 {len(page)} 个字符，超过上限 {c['一页纸上限字符']}")
    plans = []
    for t in c["发布"]["目标"]:
        p = Path(t).expanduser()
        old = p.read_text(encoding="utf-8") if p.exists() else ""
        new, err = merged(old, page)
        if err:
            errors.append(f"{p}：{err}")
        plans.append((p, old, new))
    if errors:
        print("发布前检查没通过，一个文件都没写：")
        print("\n".join(f"  - {e}" for e in errors))
        sys.exit(1)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    for p, old, new in plans:
        print(f"\n=== {p}（{'已存在' if p.exists() else '会新建'}）")
        if old == new:
            print("没有变化")
            continue
        diff = list(difflib.unified_diff(old.splitlines(), new.splitlines(), "原文件", "发布后", lineterm=""))
        print("\n".join(diff[:60]) + ("\n……" if len(diff) > 60 else ""))
        if apply:
            if p.exists():
                b = lib / "_发布备份" / stamp
                b.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, b / str(p).strip("/").replace("/", "__"))
            atomic_write(p, new)
            print("已写入")
    if not apply:
        print("\n这是演示，没有改任何文件。确认后用 --apply 真写。")


if __name__ == "__main__":
    main()
