#!/usr/bin/env python3
"""核对判断卡：结构完整（必填元数据和字段、证据行格式、编号唯一），每句原话能逐字在出处文件里找到，"一手证据"数对得上。
出处路径可以是绝对路径、~ 开头，或相对于判断库根目录的路径。
用法：核对原话.py [卡片文件 ...]      不给参数就核对全部卡片。有问题时退出码为 1。"""
import sys
from pathlib import Path
from lib import conf, card_files, load, parse, problems, firsthand


def squash(s):
    return "".join(s.split())


def main():
    if sys.argv[1:]:
        files = [Path(a) for a in sys.argv[1:]]
    else:
        lib = conf()["判断库"]
        load(lib)  # 编号重复会在这里退出
        files = card_files(lib)
        if not files:
            sys.exit(f"判断库里没有卡片：{lib / '判断卡'}（路径配错了？）")
    bad = 0
    cache = {}
    for f in files:
        meta, _, _, ev = parse(f)
        found = problems(f)
        root = f.resolve().parent.parent  # 判断库根目录（卡片在 判断卡/ 下）
        for e in ev:
            p = Path(e["path"]).expanduser()
            if not p.is_absolute():
                p = root / p
            if p not in cache:
                cache[p] = p.read_text(encoding="utf-8") if p.is_file() else None
            text = cache[p]
            if text is None:
                found.append(f"出处文件不存在：{p}")
            elif e["q"] not in text and squash(e["q"]) not in squash(text):
                found.append(f"原文里找不到：「{e['q'][:40]}」（{p.name}）")
        n = firsthand(ev)
        if str(n) != meta.get("一手证据"):
            found.append(f"一手证据应为 {n}，卡片写的是 {meta.get('一手证据')}")
        print(f"{'✅' if not found else '❌'} {f.stem}（证据 {len(ev)} 条，独立一手 {n}）")
        for p in found:
            print(f"    - {p}")
        bad += bool(found)
    print(f"\n共 {len(files)} 张，{len(files) - bad} 张通过，{bad} 张有问题")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
