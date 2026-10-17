#!/usr/bin/env python3
"""把用户在 候选箱.md 里的标注写回判断卡。
标注：收 → 已确认；不收 → 不像；改 → 待改（备注里写怎么改）。空着的不动。末尾的标点会被忽略（"收。"等于"收"）。
有任何一行看不懂（不认识的标注、编号和卡片对不上），整批都不改，退出码 1。
用法：应用标注.py"""
import datetime, re, sys
from lib import conf, load, write

STATE = {"收": "已确认", "不收": "不像", "改": "待改"}
LINK = re.compile(r"\[\[(.+?)\]\]")


def cells_of(line):
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def main():
    lib = conf()["判断库"]
    cards = {f.stem: (f, meta, body) for f, meta, body, _, _ in load(lib)}
    marks, errors = {}, []
    for line in (lib / "候选箱.md").read_text(encoding="utf-8").splitlines():
        if not line.startswith("| J-"):
            continue
        c = cells_of(line)
        if len(c) != 7:
            errors.append(f"这一行的列数不对（应为 7 列）：{line[:60]}")
            continue
        no, link, mark, note = c[0], LINK.search(c[1]), c[5].rstrip("。.，,！!；;、 "), c[6]
        if not mark:
            continue
        if mark not in STATE:
            errors.append(f"{no}：看不懂的标注「{c[5]}」（只认 收 / 不收 / 改）")
            continue
        stem = link.group(1) if link else ""
        if stem not in cards or cards[stem][1].get("编号") != no:
            errors.append(f"{no}：卡片链接「{c[1]}」和编号对不上")
            continue
        marks[stem] = (mark, note)
    if errors:
        print("候选箱里有看不懂的地方，这一批一张都没改：")
        print("\n".join(f"  - {e}" for e in errors))
        sys.exit(1)
    today = datetime.date.today().isoformat()
    changed = 0
    for stem, (mark, note) in marks.items():
        f, meta, body = cards[stem]
        if meta.get("状态") == STATE[mark]:
            continue
        meta["状态"], meta["更新"] = STATE[mark], today
        body = body.rstrip("\n") + f"\n- {today}｜你标注「{mark}」{('：' + note) if note else ''}\n"
        write(f, meta, body)
        changed += 1
        print(f"{meta['编号']} → {STATE[mark]}")
    print(f"共改了 {changed} 张卡。接着运行 一页纸.py 重新生成。")


if __name__ == "__main__":
    main()
