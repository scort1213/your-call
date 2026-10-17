#!/usr/bin/env python3
"""统计 猜中记录.md：AI 在岔路口猜你的选择，猜中了多少、问多了多少、自己定错了多少、该问没问多少。
用法：猜中统计.py <猜中记录.md> [...]      按"条件"一栏分开统计（例如"基线"和"带一页纸"）。"""
import re, sys
from pathlib import Path

KEYS = ["问你", "问你已回", "猜中", "叫多了", "自己定", "自己定已回", "走错", "漏问", "待补"]


def stats(paths):
    out = {}
    for path in paths:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
            if len(cells) != 11 or not re.match(r"P-\d+", cells[0]):
                continue
            kind, cond, chose, hit, should = cells[2], cells[7], cells[8], cells[9], cells[10]
            st = out.setdefault(cond or "未写条件", dict.fromkeys(KEYS, 0))
            if not chose:
                st["待补"] += 1
            if kind == "问你":
                st["问你"] += 1
                if chose:
                    st["问你已回"] += 1
                    st["猜中"] += hit == "是"
                    st["叫多了"] += should == "不该"
            elif kind == "自己定":
                st["自己定"] += 1
                if chose:
                    st["自己定已回"] += 1
                    st["走错"] += hit == "否"
                    st["漏问"] += should == "该"
    return out


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    rate = lambda a, b: f"{a}/{b}" if b else "无数据"
    for cond, st in stats(sys.argv[1:]).items():
        print(f"{cond}：问你 {st['问你']} 次，猜中 {rate(st['猜中'], st['问你已回'])}，叫多了 {rate(st['叫多了'], st['问你已回'])}；"
              f"自己定 {st['自己定']} 次，走错 {rate(st['走错'], st['自己定已回'])}，漏问 {st['漏问']} 次；待补 {st['待补']} 行")


if __name__ == "__main__":
    main()
