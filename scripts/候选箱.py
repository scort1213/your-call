#!/usr/bin/env python3
"""把"候选""待改"的卡挑几条列进 候选箱.md，请用户标注。一次只给几条（默认 5），证据多的先给。
先运行 应用标注.py 把旧标注写回卡片，再运行本脚本（本脚本会重写候选箱，旧标注不保留）。
用法：候选箱.py [--n 条数]"""
import datetime, sys
from lib import conf, load, atomic_write


def cell(s):
    """表格单元格：转义 |，去掉换行。"""
    return str(s).replace("\n", " ").replace("|", "\\|")


def main():
    lib = conf()["判断库"]
    limit = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 5
    todo = [(f, meta, fl) for f, meta, _, fl, _ in load(lib) if meta.get("状态") in ("候选", "待改")]
    todo.sort(key=lambda x: (-int(x[1].get("一手证据", 0)), x[1]["编号"]))
    rows = []
    for f, meta, fl in todo[:limit]:
        n = int(meta.get("一手证据", 0))
        note = "单例" if n < 2 else ""
        if meta.get("状态") == "待改":
            note = (note + " 待改").strip()
        one = fl.get("选", "") + (f"（可能冲突：{fl['可能冲突']}）" if fl.get("可能冲突") else "")
        cells = [meta["编号"], f"[[{f.stem}]]", one, meta.get("范围", ""), f"{n}{('（' + note + '）') if note else ''}", "", ""]
        rows.append("| " + " | ".join(map(cell, cells)) + " |")
    out = ["# 候选箱", "",
           f"> 更新于 {datetime.date.today().isoformat()}。在\"你的标注\"一栏填 **收 / 不收 / 改**，\"备注\"写原因或怎么改；空着表示还没看。",
           "> 点卡片名可以看原话证据。填好后告诉 Claude\"候选箱标好了\"。", ""]
    if not rows:
        out.append("现在没有待确认的候选。")
    else:
        out += ["| 编号 | 卡片 | 一句话 | 范围 | 独立一手证据 | 你的标注 | 备注 |",
                "|---|---|---|---|---|---|---|", *rows, ""]
        if len(todo) > limit:
            out.append(f"还有 {len(todo) - limit} 条候选，这几条标完后再给你看。")
    atomic_write(lib / "候选箱.md", "\n".join(out))
    print(f"候选箱：这次给 {len(rows)} 条，还剩 {len(todo) - len(rows)} 条")


if __name__ == "__main__":
    main()
