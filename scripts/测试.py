#!/usr/bin/env python3
"""回归测试：在临时目录里造一个小判断库，逐项检查脚本行为。不碰真实判断库和全局文件。
用法：测试.py [脚本目录]      默认测本目录的脚本；给旧版本的目录就能跑基线对比。"""
import os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

SCRIPTS = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent).resolve()
START, END = "<!-- 个人判断库：开始", "<!-- 个人判断库：结束 -->"
results = []


def card(no, title, quotes, state="候选", score=0, choose="一次只给一个推荐", firsthand=None, extra="", scope="通用"):
    ev = "\n".join(f"- {d}｜{src}·文件｜一手｜「{q}」｜`{SRC}`" for d, src, q in quotes)
    n = firsthand if firsthand is not None else len({(d, s) for d, s, _ in quotes})
    return (f"---\n编号: {no}\n标题: {title}\n类别: 取舍\n范围: {scope}\n批次: 1\n状态: {state}\n一手证据: {n}\n"
            f"分数: {score}\n更新: 2026-10-18\ntags: [判断]\n---\n# {no} {title}\n\n- **当**：要我做决定时\n"
            f"- **选**：{choose}\n- **而不是**：一次抛一堆方案\n- **为什么**：判断不过来\n- **适用情境**：任何时候\n"
            f"- **不适用**：待补\n{extra}\n## 证据\n\n{ev}\n\n## 记录\n\n- 2026-10-18｜测试\n")


def fresh(cards):
    """新建临时库，返回 (库路径, 目标目录)。"""
    root = Path(tempfile.mkdtemp(prefix="judgment-test-"))
    lib, tgt = root / "库", root / "目标"
    (lib / "判断卡").mkdir(parents=True)
    tgt.mkdir()
    for name, text in cards.items():
        (lib / "判断卡" / f"{name}.md").write_text(text, encoding="utf-8")
    return lib, tgt


def run(script, lib, targets, *args):
    env = dict(os.environ, JUDGMENT_LIB=str(lib), JUDGMENT_TARGETS=":".join(map(str, targets)))
    p = subprocess.run([sys.executable, str(SCRIPTS / script), *args], env=env, capture_output=True, text=True, cwd=SCRIPTS)
    return p.returncode, p.stdout + p.stderr


def text(p):
    p = Path(p)
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(f"{'✅' if ok else '❌'} {name}" + (f"\n     {detail.strip()[:300]}" if not ok and detail else ""))


def mark(lib, marks):
    """在候选箱里给指定编号填标注。marks: {编号: (标注, 备注)}"""
    p = lib / "候选箱.md"
    lines = text(p).splitlines()
    for i, l in enumerate(lines):
        for no, (m, note) in marks.items():
            if l.startswith(f"| {no} "):
                cells = re.split(r"(?<!\\)\|", l.strip().strip("|"))
                cells[-2], cells[-1] = f" {m} ", f" {note} "
                lines[i] = "|" + "|".join(cells) + "|"
    p.write_text("\n".join(lines), encoding="utf-8")


TMP = Path(tempfile.mkdtemp(prefix="judgment-src-"))
SRC = TMP / "源.md"
SRC.write_text("别一次给我五个方案，我挑不过来，一次只给一个推荐就行\n先告诉我你打算怎么做\n先跑基线\n", encoding="utf-8")
Q1 = ("2026-10-15", "甲案", "一次只给一个推荐")
Q2 = ("2026-10-18", "乙案", "先告诉我你打算怎么做")
Q3 = ("2026-10-18", "乙案", "先跑基线")
BASE = {"J-01 一次只给一个推荐": card("J-01", "一次只给一个推荐", [Q1, Q2]),
        "J-02 单例": card("J-02", "单例", [Q3], choose="先跑基线"),
        "J-03 第三张": card("J-03", "第三张", [Q1, Q3], choose="先测")}

# 1 核对：正常库通过
lib, tgt = fresh(BASE)
code, out = run("核对原话.py", lib, [])
check("核对：正常库全部通过", code == 0, out)

# 2 核对：缺必填字段要报错
bad = dict(BASE); bad["J-01 一次只给一个推荐"] = BASE["J-01 一次只给一个推荐"].replace("- **当**：要我做决定时\n", "")
lib, tgt = fresh(bad)
code, out = run("核对原话.py", lib, [])
check("核对：缺'当'字段时报错", code == 1, out)

# 3 核对：证据行格式坏了要报错
bad = dict(BASE); bad["J-01 一次只给一个推荐"] = BASE["J-01 一次只给一个推荐"].replace("2026-10-15｜甲案", "2026-10-15|甲案")
lib, tgt = fresh(bad)
code, out = run("核对原话.py", lib, [])
check("核对：证据行用了半角分隔符时报错", code == 1, out)

# 4 空库：核对、正式一页纸、发布都要拒绝
lib, tgt = fresh({})
code1, out1 = run("核对原话.py", lib, [])
code2, out2 = run("一页纸.py", lib, [])
t = tgt / "CLAUDE.md"
t.write_text(f"原有\n{START}（由 /judgment 生成，别手改） -->\n旧判断\n{END}\n", encoding="utf-8")
before = text(t)
code3, out3 = run("发布.py", lib, [t], "--apply")
check("空库：核对报错", code1 == 1, out1)
check("空库：正式一页纸拒绝生成", code2 == 1, out2)
check("空库：发布拒绝，目标不变", code3 == 1 and text(t) == before, out3)

# 5 编号重复：候选箱和应用标注都要拒绝
dup = dict(BASE); dup["J-99 重复"] = card("J-01", "重复", [Q1, Q2])
lib, tgt = fresh(dup)
code1, out1 = run("候选箱.py", lib, [])
code2, out2 = run("核对原话.py", lib, [])
check("编号重复：候选箱拒绝", code1 == 1, out1)
check("编号重复：核对报错", code2 == 1, out2)

# 6 候选箱转义 |，标注仍能读对
pipe = dict(BASE); pipe["J-01 一次只给一个推荐"] = card("J-01", "一次只给一个推荐", [Q1, Q2], choose="一次只给一个推荐 | 附上推荐")
lib, tgt = fresh(pipe)
run("候选箱.py", lib, [])
row = next((l for l in text(lib / "候选箱.md").splitlines() if l.startswith("| J-01 ")), "")
check("候选箱：单元格里的 | 被转义，列数正确", len(re.split(r"(?<!\\)\|", row.strip().strip("|"))) == 7, row)
mark(lib, {"J-01": ("收", "")})
code, out = run("应用标注.py", lib, [])
st = text(lib / "判断卡" / "J-01 一次只给一个推荐.md")
check("候选箱：含 | 的行标'收'后生效", code == 0 and "状态: 已确认" in st, out)

# 7 标注写法：'收。'要认；不认识的标注整批拒绝、不改任何卡
lib, tgt = fresh(BASE)
run("候选箱.py", lib, [])
mark(lib, {"J-01": ("收。", "")})
code, out = run("应用标注.py", lib, [])
check("标注：'收。'能识别", "状态: 已确认" in text(lib / "判断卡" / "J-01 一次只给一个推荐.md"), out)
lib, tgt = fresh(BASE)
run("候选箱.py", lib, [])
mark(lib, {"J-01": ("收", ""), "J-03": ("也许", "")})
code, out = run("应用标注.py", lib, [])
check("标注：有不认识的标注时整批拒绝，不改任何卡",
      code == 1 and "状态: 候选" in text(lib / "判断卡" / "J-01 一次只给一个推荐.md"), out)

# 8 主流程：收 / 不收 / 改 → 正式一页纸只含已确认；候选箱去掉不像
lib, tgt = fresh(BASE)
run("候选箱.py", lib, [])
mark(lib, {"J-01": ("收", ""), "J-02": ("不收", "不像我"), "J-03": ("改", "范围写清")})
code, out = run("应用标注.py", lib, [])
code2, out2 = run("一页纸.py", lib, [])
page = text(lib / "一页纸.md")
run("候选箱.py", lib, [])
box = text(lib / "候选箱.md")
check("主流程：标注写回", code == 0, out)
check("主流程：正式一页纸只含已确认（J-01）", code2 == 0 and "J-01" in page and "J-02" not in page and "J-03" not in page, page)
check("主流程：不收的卡不再进候选箱", "| J-02 " not in box and "| J-03 " in box, box)

# 9 单例被明确'收'可以进一页纸
lib, tgt = fresh(BASE)
run("候选箱.py", lib, [])
mark(lib, {"J-02": ("收", "")})
run("应用标注.py", lib, [])
run("一页纸.py", lib, [])
check("单例：你标'收'后进正式一页纸", "J-02" in text(lib / "一页纸.md"))

# 10 分数低于 0 的已确认卡不进一页纸
neg = dict(BASE); neg["J-03 第三张"] = card("J-03", "第三张", [Q1, Q3], state="已确认", score=-1, choose="先测")
neg["J-01 一次只给一个推荐"] = card("J-01", "一次只给一个推荐", [Q1, Q2], state="已确认")
lib, tgt = fresh(neg)
run("一页纸.py", lib, [])
page = text(lib / "一页纸.md")
check("分数 <0：不进一页纸", "J-01" in page and "J-03" not in page, page)

# 11 超长：一页纸不写出、旧文件不变；超长页面也发布不出去
many = {f"J-{i:02d} 卡{i}": card(f"J-{i:02d}", f"卡{i}", [Q1, Q2], state="已确认", choose="很长的选择" * 12) for i in range(1, 41)}
lib, tgt = fresh(many)
(lib / "一页纸.md").write_text("旧的一页纸\n", encoding="utf-8")
code, out = run("一页纸.py", lib, [])
check("超长：一页纸报错且旧文件不变", code == 1 and text(lib / "一页纸.md") == "旧的一页纸\n", out)
(lib / "一页纸.md").write_text("<!-- 一页纸：正式，40 条 -->\n" + "很长" * 2000, encoding="utf-8")
t = tgt / "AGENTS.md"
t.write_text("原有\n", encoding="utf-8")
code, out = run("发布.py", lib, [t], "--apply")
check("超长：发布拒绝，目标不变", code == 1 and text(t) == "原有\n", out)

# 12 预览版不能真发布
lib, tgt = fresh(BASE)
run("一页纸.py", lib, [], "--preview")
t = tgt / "AGENTS.md"
code, out = run("发布.py", lib, [t], "--apply")
check("预览版：发布拒绝", code == 1 and not t.exists(), out)

# 13 发布：演示不写；真写只改标记块、先备份、写两次无变化
conf = dict(BASE); conf["J-01 一次只给一个推荐"] = card("J-01", "一次只给一个推荐", [Q1, Q2], state="已确认")
lib, tgt = fresh(conf)
run("一页纸.py", lib, [])
t1, t2 = tgt / "CLAUDE.md", tgt / "AGENTS.md"
t2.write_text("# 原有内容\n- 用简体中文\n", encoding="utf-8")
code, out = run("发布.py", lib, [t1, t2])
check("发布演示：不写任何文件", code == 0 and not t1.exists() and text(t2) == "# 原有内容\n- 用简体中文\n", out)
code, out = run("发布.py", lib, [t1, t2], "--apply")
txt = text(t2)
check("发布真写：块外原文保留，块内是一页纸", code == 0 and txt.startswith("# 原有内容\n- 用简体中文\n") and "J-01" in txt and txt.count(START) == 1, out)
check("发布真写：已存在的文件先备份", any((lib / "_发布备份").rglob("*AGENTS.md")), out)
code, out = run("发布.py", lib, [t1, t2], "--apply")
check("发布真写：再写一次没有变化", txt == text(t2) and out.count("没有变化") == 2, out)

# 14 标记块残缺或重复：整批拒绝，哪个目标都不写
lib, tgt = fresh(conf)
run("一页纸.py", lib, [])
half = tgt / "half.md"
half.write_text(f"前文\n{START}（由 /judgment 生成，别手改） -->\n残缺旧内容\n", encoding="utf-8")
ok_t = tgt / "ok.md"
code, out = run("发布.py", lib, [ok_t, half], "--apply")
check("标记块残缺：拒绝，所有目标都不写", code == 1 and not ok_t.exists() and text(half).count(START) == 1, out)

# 15 两个目标同名（不同文件夹）：备份不互相覆盖
lib, tgt = fresh(conf)
run("一页纸.py", lib, [])
(tgt / "a").mkdir(); (tgt / "b").mkdir()
ta, tb = tgt / "a" / "AGENTS.md", tgt / "b" / "AGENTS.md"
ta.write_text("甲\n", encoding="utf-8"); tb.write_text("乙\n", encoding="utf-8")
run("发布.py", lib, [ta, tb], "--apply")
backups = sorted(p.read_text(encoding="utf-8") for p in (lib / "_发布备份").rglob("*") if p.is_file())
check("同名目标：两份备份都在", backups == ["乙\n", "甲\n"], str(backups))

# 16 领域卡不进全局一页纸
dom = {"J-01 一次只给一个推荐": card("J-01", "一次只给一个推荐", [Q1, Q2], state="已确认"),
       "J-02 生图专用": card("J-02", "生图专用", [Q1, Q2], state="已确认", choose="多生成", scope="生图")}
lib, tgt = fresh(dom)
run("一页纸.py", lib, [])
page = text(lib / "一页纸.md")
check("领域卡：不进全局一页纸", "J-01" in page and "J-02" not in page, page)

# 17 候选箱一次只给几条，证据多的先给
many5 = {f"J-{i:02d} 卡{i}": card(f"J-{i:02d}", f"卡{i}", [Q1, Q2] if i % 2 else [Q1]) for i in range(1, 9)}
lib, tgt = fresh(many5)
code, out = run("候选箱.py", lib, [])
rows = [l for l in text(lib / "候选箱.md").splitlines() if l.startswith("| J-")]
check("候选箱：默认一次 5 条，证据多的在前", len(rows) == 5 and rows[0].startswith("| J-01 ") and "还有 3 条" in text(lib / "候选箱.md"), out)

# 18 出处可以写相对于判断库根目录的路径
lib, tgt = fresh({})
(lib / "原话").mkdir()
(lib / "原话" / "聊天.md").write_text("一次只给一个推荐\n先告诉我你打算怎么做\n", encoding="utf-8")
rel = card("J-01", "相对路径", [Q1, Q2]).replace(f"`{SRC}`", "`原话/聊天.md`")
(lib / "判断卡" / "J-01 相对路径.md").write_text(rel, encoding="utf-8")
code, out = run("核对原话.py", lib, [])
check("核对：出处可以写相对路径", code == 0, out)

# 19 猜中统计
led = TMP / "猜中记录.md"
led.write_text("\n".join([
    "| P-01 | 10:00 | 问你 | 甲 | A | — | 高 | 基线 | A | 是 | 该 |",
    "| P-02 | 10:10 | 问你 | 乙 | A | — | 中 | 基线 | B | 否 | 不该 |",
    "| P-03 | 10:20 | 问你 | 丙 | A \\| B | — | 低 | 基线 |  |  |  |",
    "| P-04 | 10:30 | 自己定 | 丁 | 做 | — | 高 | 基线 | 推翻 | 否 | 该 |",
    "| P-05 | 10:40 | 问你 | 戊 | A | J-01 | 中 | 带一页纸 | A | 是 | 该 |"]), encoding="utf-8")
p = subprocess.run([sys.executable, str(SCRIPTS / "猜中统计.py"), str(led)], capture_output=True, text=True)
check("猜中统计：按条件分开算对", "基线：问你 3 次，猜中 1/2，叫多了 1/2；自己定 1 次，走错 1/1，漏问 1 次；待补 1 行" in p.stdout
      and "带一页纸：问你 1 次，猜中 1/1" in p.stdout, p.stdout + p.stderr)

passed = sum(ok for _, ok in results)
print(f"\n共 {len(results)} 项，通过 {passed} 项，失败 {len(results) - passed} 项")
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(0 if passed == len(results) else 1)
