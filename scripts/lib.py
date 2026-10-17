"""判断库脚本共用的读写函数。"""
import os, re, sys, tempfile, tomllib
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
EVIDENCE = re.compile(r'^- (?P<date>[^｜]+)｜(?P<src>[^｜]+)｜(?P<kind>[^｜]+)｜「(?P<q>.+)」｜`(?P<path>[^`]+)`$')
FIELD = re.compile(r'^- \*\*(?P<k>[^*]+)\*\*：(?P<v>.*)$')
GROUPS = ["关键节点", "问法", "取舍", "目标"]
REQUIRED_META = ["编号", "标题", "类别", "范围", "状态", "一手证据", "分数"]
REQUIRED_FIELDS = ["当", "选", "而不是"]
PAGE_MARK = re.compile(r"^<!-- 一页纸：(?P<kind>正式|预览)，(?P<n>\d+) 条 -->")


def conf():
    """读配置。测试时可用环境变量 JUDGMENT_LIB、JUDGMENT_TARGETS（冒号分隔，路径里不能有冒号）换成临时位置。"""
    c = tomllib.load(open(SKILL / "配置.toml", "rb"))
    c["判断库"] = Path(os.environ.get("JUDGMENT_LIB") or c["判断库"]).expanduser()
    if os.environ.get("JUDGMENT_TARGETS"):
        c["发布"]["目标"] = os.environ["JUDGMENT_TARGETS"].split(":")
    return c


def card_files(lib):
    return sorted((lib / "判断卡").glob("J-*.md"))


def section(body, title):
    """取正文里某个 ## 小节下面的非空行。"""
    out, inside = [], False
    for line in body.splitlines():
        if line.startswith("## "):
            inside = line[3:].strip() == title
        elif inside and line.strip():
            out.append(line)
    return out


def parse(path):
    """返回 (元数据, 正文, 字段, 证据列表)。"""
    text = Path(path).read_text(encoding="utf-8")
    meta, body = {}, text
    if text.startswith("---\n") and "\n---\n" in text[4:]:
        head, body = text[4:].split("\n---\n", 1)
        for line in head.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.split("#")[0].strip()
    fields = {m["k"]: m["v"].strip() for m in map(FIELD.match, body.splitlines()) if m}
    evidence = [m.groupdict() for m in map(EVIDENCE.match, section(body, "证据")) if m]
    return meta, body, fields, evidence


def problems(path):
    """卡片结构上的问题（不查原话是否存在）。"""
    meta, body, fields, ev = parse(path)
    out = [f"缺元数据：{k}" for k in REQUIRED_META if not meta.get(k)]
    out += [f"缺字段：{k}" for k in REQUIRED_FIELDS if not fields.get(k)]
    bad = [l for l in section(body, "证据") if not EVIDENCE.match(l)]
    out += [f"证据行格式不对：{l[:40]}" for l in bad]
    if not ev:
        out.append("没有证据行")
    if meta.get("编号") and not Path(path).stem.startswith(meta["编号"] + " "):
        out.append(f"文件名和编号对不上：{Path(path).stem}")
    return out


def load(lib):
    """读全部卡片；编号重复就退出。返回 [(路径, 元数据, 正文, 字段, 证据)]。"""
    cards = [(f, *parse(f)) for f in card_files(lib)]
    seen = {}
    for f, meta, *_ in cards:
        seen.setdefault(meta.get("编号"), []).append(f.stem)
    dup = {k: v for k, v in seen.items() if len(v) > 1}
    if dup:
        sys.exit("编号重复，先改成唯一再继续：" + "；".join(f"{k}：{'、'.join(v)}" for k, v in dup.items()))
    return cards


def write(path, meta, body):
    head = "\n".join(f"{k}: {v}" for k, v in meta.items())
    atomic_write(path, f"---\n{head}\n---\n{body}")


def atomic_write(path, text):
    """先写临时文件再替换，写到一半中断也不会留下半个文件。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def firsthand(evidence):
    """独立的一手依据数：一手证据按"日期 + 出处（· 之前）"去重。"""
    return len({(e["date"], e["src"].split("·")[0]) for e in evidence if e["kind"].startswith("一手")})
