#!/usr/bin/env python3
"""eca — Expert Process 工具包的本机命令（只用 Python 标准库，兼容 3.9）。

确定性操作在这里完成，只把简短结果回传给模型：
  new     建档案 runs/<日期>_<slug>/（1_简报 2_作战图 3_日志 4_验收复盘）
  status  看档案进度；不带参数看最近改过的档案
  gate    往日志追加一条关卡记录
  card    在档案里按模板建流程卡 / 专家卡 / 偏好卡
  find    在库里查卡片
  save    把档案里的卡片入库并重建索引
  index   重建 library/INDEX.md
  check   结构检查（技能目录 / 档案 / 卡片）+ 漏问、漏回写提醒
  stats   汇总所有档案的关卡与"改变方向"次数
  pack    导出 dist/：技能 zip + 单文件版

v0.3（2026-10-21）：档案从 7 个文件改为 4 个活文档；新增偏好卡、gate、stats。
v0.2 结构的旧档案（00_定位 … 06_复盘）仍可 status / check / stats。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skill" / "expert-process"
TEMPLATES = ROOT / "templates"
LIBRARY = ROOT / "library"
RUNS = ROOT / "runs"
DIST = ROOT / "dist"

TODO = "（待填）"
STAGES = ["1_简报.md", "2_作战图.md", "3_日志.md", "4_验收复盘.md"]
BRIEF, PLAN, LOG, REVIEW = STAGES
LEGACY_STAGES = ["00_定位.md", "01_流程.md", "02_专家.md", "03_整合.md", "04_执行.md", "05_验收.md", "06_复盘.md"]
CARD_TYPES = {"process": "processes", "expert": "experts", "preference": "preferences"}
CARD_NAMES = {"process": "流程卡", "expert": "专家卡", "preference": "偏好卡"}
CARD_REQUIRED = ["type", "id", "title", "domain", "updated", "confidence"]
CONFIDENCE = {"高", "中", "低"}
DECISION_TYPES = {"算", "查", "问", "确认"}
PREF_STATES = {"有效", "待确认", "已推翻"}
GATE_FIELDS = ["给了", "答", "没问会怎样", "改变方向", "回写"]
GATE_META = ["状态", "登记方式", "关联决定", "等待秒数", "登记时间"]
MODULE_FIELDS = ["目标", "输入", "职责", "处理", "输出", "验收", "交接"]
PHASE_STATES = {"未开始", "进行中", "待用户", "已完成", "已裁剪", "需重做"}
ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
GATE_ID_RE = re.compile(r"^G\d+$")
SKILL_KEYS = {"name", "description", "license", "allowed-tools", "metadata"}
STALE_DAYS = 180       # 行业卡
PREF_STALE_DAYS = 90   # 偏好条目


# ---------- 小工具 ----------

def today() -> str:
    return dt.date.today().isoformat()


def rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""


def strip_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def split_frontmatter(text: str):
    """返回 (frontmatter dict, frontmatter 原文行列表, 正文)。不是 --- 开头则 dict 为 None。"""
    if not text.startswith("---\n"):
        return None, [], text
    end = text.find("\n---", 4)
    if end == -1:
        return None, [], text
    raw = text[4:end]
    body = text[end + 4:].lstrip("\n")
    data: dict = {}
    lines = raw.splitlines()
    for line in lines:
        if not line.strip() or line.startswith((" ", "\t")):
            continue  # 嵌套结构（如 metadata）只认顶层键
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        val = val.strip()
        if val.startswith("[") and val.endswith("]"):
            items = [v.strip().strip("'\"") for v in val[1:-1].split(",")]
            data[key.strip()] = [v for v in items if v]
        else:
            data[key.strip()] = val.strip("'\"")
    return data, lines, body


def write_frontmatter(data: dict, order: list, body: str) -> str:
    keys = [k for k in order if k in data] + [k for k in data if k not in order]
    out = ["---"]
    for k in keys:
        v = data[k]
        out.append(f"{k}: [{', '.join(v)}]" if isinstance(v, list) else f"{k}: {v}")
    out.append("---")
    return "\n".join(out) + "\n\n" + body


def table_rows(section: str) -> list:
    """Markdown 表格的数据行（跳过表头与分隔行），返回单元格列表。"""
    rows = []
    lines = [l.strip() for l in section.splitlines() if l.strip().startswith("|")]
    for i, l in enumerate(lines):
        cells = [c.strip() for c in l.strip("|").split("|")]
        if i == 0 or set("".join(cells)) <= set("-: "):
            continue
        rows.append(cells)
    return rows


def table_records(text: str) -> list:
    """按表头取字段；兼容老表格，避免增加列后把状态读错。"""
    lines = [line.strip() for line in text.splitlines() if line.strip().startswith("|")]
    if not lines:
        return []
    headers = [cell.strip() for cell in lines[0].strip("|").split("|")]
    return [dict(zip(headers, cells)) for cells in table_rows(text)]


def filled(value: str) -> bool:
    return bool(value and value.strip() not in {"—", "-"} and TODO not in value)


def field_text(value: str) -> str:
    """关卡字段保持单行，避免回答中的标题变成另一条日志事件。"""
    return value.replace("\r", "").replace("\n", " / ").strip()


def section(text: str, title: str) -> str:
    m = re.search(rf"^##\s+{re.escape(title)}\s*$(.*?)(?=^##\s|\Z)", text, flags=re.M | re.S)
    return m.group(1) if m else ""


def run_mtime(run: Path) -> float:
    times = [p.stat().st_mtime for p in run.rglob("*") if p.is_file() and not p.name.startswith(".")]
    return max(times) if times else run.stat().st_mtime


def all_runs() -> list:
    return sorted(d for d in RUNS.iterdir() if d.is_dir() and not d.name.startswith((".", "_"))) if RUNS.exists() else []


def resolve_run(arg) -> Path:
    if arg:
        p = Path(arg)
        if not p.is_absolute():
            p = RUNS / arg if (RUNS / arg).exists() else (Path.cwd() / arg)
        if not p.is_dir():
            sys.exit(f"找不到档案：{arg}")
        return p.resolve()
    runs = all_runs()
    if not runs:
        sys.exit("runs/ 下还没有档案，先用 new 建一个")
    return max(runs, key=run_mtime)  # 最近改过的，而不是名字排最后的


def is_legacy(run: Path) -> bool:
    return (run / LEGACY_STAGES[0]).exists() and not (run / BRIEF).exists()


def card_files(folder: Path):
    return sorted(p for p in folder.glob("*.md") if not p.name.startswith((".", "_")))


def days_since(date: str):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        return None
    try:
        return (dt.date.today() - dt.date.fromisoformat(date)).days
    except ValueError:
        return None


# ---------- 解析档案 ----------

def parse_gates(text: str) -> list:
    """按G编号归并追加事件；事前方案保留在早先事件，答复只追加。"""
    text = strip_comments(text)
    gates = {}
    for m in re.finditer(r"^###[ \t]+(G\d+)[ \t]+([^\n]*)\n(.*?)(?=^###[ \t]|\Z)", text, flags=re.M | re.S):
        head, body = m.group(2), m.group(3)
        kind = re.search(r"（(问|确认|行业关卡)）", head)
        g = {"id": m.group(1), "title": re.sub(r"（.*?）|—.*$", "", head).strip(),
             "type": kind.group(1) if kind else "", "fields": {}}
        for f in GATE_FIELDS + GATE_META:
            fm = re.search(rf"^-\s*{re.escape(f)}：(.*)$", body, flags=re.M)
            g["fields"][f] = fm.group(1).strip() if fm else ""
        g["status"] = g["fields"].get("状态") or ("已答" if filled(g["fields"].get("答", "")) else "待答")
        g["basis"] = g["fields"].get("登记方式") or "未知"
        previous = gates.get(g["id"])
        g["events"] = (previous["events"] if previous else []) + [g["fields"].copy()]
        gates[g["id"]] = g
    return list(gates.values())


def legacy_gates(run: Path) -> list:
    """v0.2 的 关卡记录.md：## G1 标题；事后补记的「- 改变方向：是/否」也认。"""
    text = read(run / "关卡记录.md")
    out = []
    for m in re.finditer(r"^##\s+(G\d+)\s*(.*?)$(.*?)(?=^##\s|\Z)", text, flags=re.M | re.S):
        ch = re.search(r"^-\s*改变方向：(.*)$", m.group(3), flags=re.M)
        answer = bool(re.search(r"^-\s*答(?:（[^）]*）)?[：:]", m.group(3), flags=re.M))
        out.append({"id": m.group(1), "title": m.group(2).strip(), "type": "",
                    "status": "已答" if answer else "未知", "basis": "回顾" if re.search(r"复盘|补记", m.group(3)) else "未知",
                    "fields": {"改变方向": ch.group(1).strip() if ch else ""}})
    return out


def parse_decisions(text: str) -> list:
    out = []
    for row in table_records(section(text, "决策登记")):
        if not row.get("#", "").startswith("D"):
            continue
        out.append({"id": row["#"], **{key: row.get(key, "") for key in ["决定", "类型", "次序", "状态"]},
                    "依据": row.get("依据 / 由谁定", row.get("依据", ""))})
    return out


def log_entries(text: str) -> int:
    return len(re.findall(r"^###\s", strip_comments(text), flags=re.M))


def decision_answered(decision: dict, gates: dict) -> bool:
    matched = re.search(r"已答\s*(G\d+)", decision["状态"])
    gate = gates.get(matched.group(1)) if matched else None
    if not gate or gate["status"] != "已答" or gate["fields"].get("关联决定") != decision["id"]:
        return False
    kinds = {"确认"} if decision["类型"] == "确认" else {"问", "行业关卡"}
    return gate["type"] in kinds


def assumption_authorized(decision: dict, brief: str) -> bool:
    return decision["类型"] == "问" and "假设" in decision["状态"] and bool(
        re.search(r"^\s*-\s*自主推进：已授权(?:\s|[；，。（(]|$)", strip_comments(brief), flags=re.M))


# ---------- 检查 ----------

def check_card(path: Path):
    errors, warns = [], []
    data, _, body = split_frontmatter(read(path))
    if data is None:
        return [f"{rel(path)}: 缺少 --- 头部"], []
    for k in CARD_REQUIRED:
        if not data.get(k) or data.get(k) == TODO:
            errors.append(f"{rel(path)}: 缺少字段 {k}")
    if data.get("type") and data["type"] not in CARD_TYPES:
        errors.append(f"{rel(path)}: type 只能是 process、expert 或 preference")
    if data.get("id") and data["id"] != TODO and not ID_RE.match(data["id"]):
        errors.append(f"{rel(path)}: id 只能用小写字母、数字、连字符")
    if data.get("confidence") and data["confidence"] not in CONFIDENCE:
        errors.append(f"{rel(path)}: confidence 只能是 高/中/低")
    if data.get("updated") and days_since(data["updated"]) is None:
        errors.append(f"{rel(path)}: updated 要写成 YYYY-MM-DD")
    n = body.count(TODO)
    if n:
        warns.append(f"{rel(path)}: 还有 {n} 处（待填）")
    if data.get("type") == "preference":
        scope = data.get("scope", "project")
        if scope not in {"project", "cross-project"}:
            errors.append(f"{rel(path)}: scope 只能是 project 或 cross-project")
        # scope描述适用范围，不决定存储服务，也不触发全局写入。
        # 未标注的旧卡按项目上下文读取，不因新增字段阻断历史档案。
        if data.get("storage", "workspace") != "workspace" and not filled(data.get("source_ref", "")):
            errors.append(f"{rel(path)}: 引用卡缺少 source_ref，请提供可追溯的文件或来源标识")
        for cells in table_rows(section(body, "偏好条目")):
            if len(cells) < 4 or TODO in cells[0]:
                continue
            item, state, date = cells[0], cells[1], cells[2]
            if state not in PREF_STATES:
                warns.append(f"{rel(path)}: 偏好「{item}」状态应为 有效/待确认/已推翻")
            d = days_since(date)
            if d is None:
                warns.append(f"{rel(path)}: 偏好「{item}」日期要写成 YYYY-MM-DD")
            elif state == "有效" and d > PREF_STALE_DAYS:
                warns.append(f"{rel(path)}: 偏好「{item}」已 {d} 天未确认，建议放进第一个关卡")
    return errors, warns


# Structural rules reimplemented from OpenAI skill-creator at revision
# 49f948faa9258a0c61caceaf225e179651397431 (Apache-2.0), extended here with
# module interfaces and local Markdown checks. See LICENSE and NOTICE.
def check_skill(folder: Path):
    errors, warns = [], []
    md = folder / "SKILL.md"
    if not md.exists():
        return [f"{rel(folder)}: 没有 SKILL.md"], []
    text = read(md)
    data, _, body = split_frontmatter(text)
    if data is None:
        return [f"{rel(md)}: 缺少 --- 头部"], []
    extra = set(data) - SKILL_KEYS
    if extra:
        errors.append(f"{rel(md)}: 头部有不支持的键 {sorted(extra)}")
    name = data.get("name", "")
    if not name:
        errors.append(f"{rel(md)}: 缺少 name")
    else:
        if not ID_RE.match(name):
            errors.append(f"{rel(md)}: name 只能用小写字母、数字、单个连字符")
        if len(name) > 64:
            errors.append(f"{rel(md)}: name 超过 64 字符")
        if name != folder.name:
            warns.append(f"{rel(md)}: name 与文件夹名 {folder.name} 不一致")
    desc = data.get("description", "")
    if not desc:
        errors.append(f"{rel(md)}: 缺少 description")
    else:
        if "<" in desc or ">" in desc:
            errors.append(f"{rel(md)}: description 不能含尖括号")
        if len(desc) > 1024:
            errors.append(f"{rel(md)}: description {len(desc)} 字符，超过 1024")
    lines = body.count("\n") + 1
    if lines > 500:
        warns.append(f"{rel(md)}: 正文 {lines} 行，超过 500 行建议拆分")
    for target in re.findall(r"\]\(([^)#\s]+)\)", text):
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        if not (folder / target).exists():
            errors.append(f"{rel(md)}: 链接的文件不存在 {target}")
    for ref in sorted((folder / "references").glob("*.md")) if (folder / "references").exists() else []:
        if ref.name not in text:
            warns.append(f"{rel(ref)}: SKILL.md 没有提到它，模型可能不知道何时读")
        if (folder / "references" / "workflow.md").exists():
            interface = {cells[0]: cells[1] for cells in table_rows(section(read(ref), "模块接口")) if len(cells) >= 2}
            missing = [field for field in MODULE_FIELDS if not filled(interface.get(field, ""))]
            if missing:
                errors.append(f"{rel(ref)}: 模块接口缺 {'、'.join(missing)}")
    return errors, warns


def check_run(run: Path):
    errors, warns = [], []
    if is_legacy(run):
        for s in LEGACY_STAGES:
            if not (run / s).exists():
                errors.append(f"{rel(run)}: 缺少 {s}")
    else:
        for s in STAGES:
            if not (run / s).exists():
                errors.append(f"{rel(run)}: 缺少 {s}")
        log = read(run / LOG)
        gates = parse_gates(log)
        gates_by_id = {gate["id"]: gate for gate in gates}
        if log_entries(log):
            for s in (BRIEF, PLAN):
                n = read(run / s).count(TODO)
                if n:
                    warns.append(f"{rel(run)}: 日志已开始，{s} 还有 {n} 处（待填）——活文档没有跟上")
                if (run / s).exists() and (run / LOG).stat().st_mtime > (run / s).stat().st_mtime:
                    warns.append(f"{rel(run)}: 日志比{s}新，请核对约束是否已回写（时间提醒，不证明漏写）")
        for d in parse_decisions(read(run / PLAN)):
            if TODO in d["决定"] or not d["决定"]:
                continue
            if d["类型"] not in DECISION_TYPES:
                warns.append(f"{rel(run)}: 决策 {d['id']} 类型应为 算/查/问/确认")
            elif d["类型"] in {"问", "确认"}:
                if not decision_answered(d, gates_by_id) and not assumption_authorized(d, read(run / BRIEF)):
                    warns.append(f"{rel(run)}: 决策 {d['id']}「{d['决定']}」是\"{d['类型']}\"类，还没有用户答案或有效授权")
        for g in gates:
            empty = [f for f in GATE_FIELDS if not g["fields"].get(f) or TODO in g["fields"][f]]
            if empty:
                warns.append(f"{rel(run)}: 关卡 {g['id']} 缺 {'、'.join(empty)}")
            if g["status"] != "已答":
                warns.append(f"{rel(run)}: 关卡 {g['id']} 待用户答复，等待时长不构成答案或许可")
        phase_section = section(read(run / PLAN), "阶段交接")
        phases = table_records(phase_section)
        if not phases:
            warns.append(f"{rel(run)}: 缺少阶段交接表，无法核对阶段接口")
        phase_ids = set()
        for phase in phases:
            phase_id = phase.get("阶段", "")
            if not filled(phase_id) or phase_id in phase_ids:
                warns.append(f"{rel(run)}: 阶段名称为空或重复")
            phase_ids.add(phase_id)
            missing_headers = [key for key in [*MODULE_FIELDS, "状态"] if key not in phase]
            if missing_headers:
                warns.append(f"{rel(run)}: 阶段交接表缺字段 {'、'.join(missing_headers)}")
            state = phase.get("状态", "")
            if state not in PHASE_STATES:
                warns.append(f"{rel(run)}: 阶段{phase.get('阶段', '?')}状态不在约定范围")
            if state == "已完成":
                missing = [key for key in MODULE_FIELDS if not filled(phase.get(key, ""))]
                if missing:
                    warns.append(f"{rel(run)}: 阶段{phase.get('阶段', '?')}已完成却缺 {'、'.join(missing)}")
    for c in card_files(run / "cards") if (run / "cards").exists() else []:
        e, w = check_card(c)
        errors += e
        warns += w
    return errors, warns


# ---------- 命令 ----------

def cmd_new(a):
    slug = re.sub(r"[\s/\\]+", "-", a.slug.strip()).strip("-")
    if not slug:
        sys.exit("slug 不能为空")
    run = RUNS / f"{today()}_{slug}"
    if run.exists():
        sys.exit(f"已存在：{rel(run)}")
    title = a.title or slug
    shutil.copytree(TEMPLATES / "dossier", run)
    for p in run.glob("*.md"):
        p.write_text(read(p).replace("{title}", title).replace("{date}", today()), encoding="utf-8")
    for keep in run.rglob(".keep"):
        keep.unlink()
    print(f"已建档案：{rel(run)}")
    print("下一步：find 查库（含偏好卡），填 1_简报.md")


def stage_state(p: Path) -> str:
    if not p.exists():
        return "缺失"
    n = read(p).count(TODO)
    return "已填写（未据此判定验收）" if n == 0 else f"待填 {n}"


def cmd_status(a):
    run = resolve_run(a.run)
    legacy = is_legacy(run)
    print(f"档案：{rel(run)}" + ("（v0.2 旧结构）" if legacy else ""))
    if legacy:
        for s in LEGACY_STAGES:
            print(f"  {s:<10} {stage_state(run / s)}")
        print(f"  关卡       {len(legacy_gates(run))} 个（关卡记录.md）")
    else:
        for s in (BRIEF, PLAN):
            print(f"  {s:<10} {stage_state(run / s)}")
        log = read(run / LOG)
        gates = parse_gates(log)
        print(f"  {LOG:<10} {log_entries(log)} 条记录，其中关卡 {len(gates)} 个")
        pending_gates = [gate for gate in gates if gate["status"] != "已答"]
        print(f"  待答关卡   {len(pending_gates)} 个")
        if pending_gates:
            print("  等待状态   待用户答复；不自动选择")
            for gate in gates:
                if gate["status"] == "已答":
                    continue
                wait = gate["fields"].get("等待秒数", "不限")
                note = "无额外超时" if wait == "不限" else f"{wait}秒提醒，到期仍待答"
                print(f"    {gate['id']}：{note}")
        print(f"  {REVIEW:<10} {stage_state(run / REVIEW)}")
        ds = [d for d in parse_decisions(read(run / PLAN)) if d["决定"] and TODO not in d["决定"]]
        if ds:
            ask = [d for d in ds if d["类型"] == "问"]
            gates_by_id = {gate["id"]: gate for gate in gates}
            open_ = []
            for decision in ask:
                if not decision_answered(decision, gates_by_id) and not assumption_authorized(decision, read(run / BRIEF)):
                    open_.append(decision)
            print(f"  决策登记   {len(ds)} 条；问 {len(ask)} 条，待答 {len(open_)} 条")
    outs = [p for p in (run / "outputs").rglob("*") if p.is_file()] if (run / "outputs").exists() else []
    cards = card_files(run / "cards") if (run / "cards").exists() else []
    print(f"  outputs/   {len(outs)} 个文件")
    print(f"  cards/     {len(cards)} 张卡" + (f"：{', '.join(c.stem for c in cards)}" if cards else ""))


def cmd_gate(a):
    run = resolve_run(a.run)
    if is_legacy(run):
        sys.exit("v0.2 旧结构的档案不支持 gate，请手动写进 关卡记录.md")
    if not GATE_ID_RE.match(a.id):
        sys.exit("关卡编号写成 G1、G2 …")
    log_path = run / LOG
    log = read(log_path)
    previous = next((gate for gate in parse_gates(log) if gate["id"] == a.id), None)
    if previous and not a.resolve:
        sys.exit(f"{a.id} 已经记过了；要改就直接编辑 {LOG}")
    if a.resolve and not previous:
        sys.exit(f"{a.id} 尚未登记，不能凭空追加答复")
    if a.resolve and (previous["status"] == "已答" or not filled(a.answer)):
        sys.exit("答复必须非空，且关卡尚未回答")
    if a.resolve and (a.gave or a.counterfactual or a.wait_seconds is not None):
        sys.exit("答复只能追加；不能改写事前选项、默认方案或等待策略")
    if not previous and not a.title:
        sys.exit("新关卡需要 --title")
    if a.type not in ("问", "确认", "行业关卡"):
        sys.exit("类型只能是 问 / 确认 / 行业关卡")
    if a.changed and a.changed not in ("是", "否", "未知"):
        sys.exit("--changed 只能是 是、否 或 未知")
    if a.wait_seconds is not None and a.wait_seconds < 0:
        sys.exit("--wait-seconds 不能为负数")
    if a.decision and not re.fullmatch(r"D\d+", a.decision):
        sys.exit("--decision 写成 D1、D2 …")
    if a.changed and not filled(a.answer):
        sys.exit("没有用户答案不能标记改变方向")
    vals = [a.gave, a.answer, a.counterfactual, a.changed, a.writeback]
    basis = "回顾" if filled(a.answer) else "事前" if filled(a.gave) and filled(a.counterfactual) else "未知"
    wait = str(a.wait_seconds) if a.wait_seconds is not None else "不限"
    decision, title, kind = a.decision, a.title, a.type
    if previous:
        old = previous["fields"]
        vals = [old.get("给了", ""), a.answer, old.get("没问会怎样", ""), a.changed, a.writeback]
        basis, wait = previous["basis"], old.get("等待秒数", "不限")
        decision, title, kind = old.get("关联决定", ""), previous["title"], previous["type"]
    lines = [f"\n### {a.id} {field_text(title)}（{kind}）— {today()}"]
    lines += [f"- {field}：{field_text(value) if value else TODO}" for field, value in zip(GATE_FIELDS, vals)]
    meta = ["已答" if filled(a.answer) else "待答", basis, decision or "—", wait, dt.datetime.now(dt.timezone.utc).isoformat()]
    lines += [f"- {field}：{value}" for field, value in zip(GATE_META, meta)]
    log_path.write_text(log.rstrip("\n") + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
    print(f"已记关卡 {a.id} → {rel(log_path)}")
    if filled(a.answer) and not a.writeback:
        print("提醒：回写为空。把答案写进 1_简报 / 2_作战图 / 偏好卡后补上")


def cmd_card(a):
    run = resolve_run(a.run)
    if a.type not in CARD_TYPES:
        sys.exit("类型只能是 process、expert 或 preference")
    if not ID_RE.match(a.id):
        sys.exit("id 只能用小写字母、数字、连字符")
    dest = run / "cards" / f"{a.id}.md"
    if dest.exists():
        sys.exit(f"已存在：{rel(dest)}")
    dest.parent.mkdir(exist_ok=True)
    text = read(TEMPLATES / "cards" / f"{a.type}.md")
    text = text.replace("{date}", today()).replace("id: （待填）", f"id: {a.id}", 1)
    if a.type == "preference":
        text = text.replace("scope: project", f"scope: {a.scope}")
        if a.source_ref:
            text = text.replace("storage: workspace", "storage: reference\nsource_ref: " + field_text(a.source_ref))
            text = re.sub(r"## 偏好条目[\s\S]*?(?=## )", "## 来源引用\n通过source_ref定位资料，核对适用条件、日期与未知；来源不可访问时如实说明。\n\n", text, count=1)
    dest.write_text(text, encoding="utf-8")
    print(f"已建卡片：{rel(dest)}")


def library_cards():
    for sub in CARD_TYPES.values():
        folder = LIBRARY / sub
        if folder.exists():
            yield from card_files(folder)


def cmd_find(a):
    words = [w.lower() for w in a.words]
    hits = 0
    for c in library_cards():
        text = read(c)
        if all(w in text.lower() for w in words):
            data, _, _ = split_frontmatter(text)
            data = data or {}
            limit = PREF_STALE_DAYS if data.get("type") == "preference" else STALE_DAYS
            d = days_since(data.get("updated", ""))
            mark = "  可能过期" if d is not None and d > limit else ""
            print(f"[{CARD_NAMES.get(data.get('type'), '?')}] {data.get('id', c.stem)} | {data.get('title','')} | "
                  f"{data.get('updated','')} | 可信度{data.get('confidence','?')}{mark} | {rel(c)}")
            hits += 1
    if not hits:
        print("库里没有匹配的卡片")
    print("范围：本命令查本地卡与来源引用，不联网检索，也不自动写入跨项目存储。")


def build_index():
    rows = {k: [] for k in CARD_TYPES}
    for c in library_cards():
        data, _, _ = split_frontmatter(read(c))
        if data and data.get("type") in rows:
            rows[data["type"]].append((data, c))
    out = ["# 卡片索引", "", f"由 `eca index` 生成于 {today()}，不要手改。", ""]
    for t, items in rows.items():
        out += [f"## {CARD_NAMES[t]}（{len(items)}）", "", "| id | 标题 | 领域 | 标签 | 更新 | 可信度 | 用过的档案 |",
                "|---|---|---|---|---|---|---|"]
        for d, c in sorted(items, key=lambda x: x[0].get("id", "")):
            tags = ", ".join(d.get("tags", [])) if isinstance(d.get("tags"), list) else d.get("tags", "")
            used = ", ".join(d.get("used_in", [])) if isinstance(d.get("used_in"), list) else d.get("used_in", "")
            out.append(f"| [{d.get('id')}]({rel(c).replace('library/', '', 1)}) | {d.get('title','')} | {d.get('domain','')} | "
                       f"{tags} | {d.get('updated','')} | {d.get('confidence','')} | {used} |")
        out.append("")
    LIBRARY.mkdir(exist_ok=True)
    (LIBRARY / "INDEX.md").write_text("\n".join(out), encoding="utf-8")
    return sum(len(v) for v in rows.values())


def cmd_index(a):
    print(f"索引已重建：{build_index()} 张卡")


def cmd_save(a):
    run = resolve_run(a.run)
    cards = card_files(run / "cards") if (run / "cards").exists() else []
    if not cards:
        sys.exit("这个档案的 cards/ 里没有卡片")
    bad = []
    for c in cards:
        e, w = check_card(c)
        bad += e + [x for x in w if "（待填）" in x]
        incoming, _, _ = split_frontmatter(read(c))
        if incoming and incoming.get("type") == "preference":
            existing, _, _ = split_frontmatter(read(LIBRARY / "preferences" / f"{incoming.get('id')}.md"))
            if existing and existing.get("scope") and not incoming.get("scope"):
                bad.append(f"{rel(c)}: 旧条目未标适用范围，不能静默覆盖已标范围的卡；核对后明确填写scope")
    if bad:
        print("有问题，先修好再入库：")
        print("\n".join(f"  {x}" for x in bad))
        sys.exit(1)
    for c in cards:
        data, _, body = split_frontmatter(read(c))
        dest = LIBRARY / CARD_TYPES[data["type"]] / f"{data['id']}.md"
        used = [run.name]
        if dest.exists():
            old, _, _ = split_frontmatter(read(dest))
            prev = old.get("used_in", []) if old else []
            used = list(dict.fromkeys((prev if isinstance(prev, list) else [prev]) + used))
            stamp = f"{dt.datetime.now():%H%M%S%f}"
            previous_date = (old or {}).get("updated", "old")
            if days_since(previous_date) is None:
                previous_date = "old"
            base = f"{data['id']}_{previous_date}_{stamp}"
            hist = LIBRARY / "_history" / f"{base}.md"
            suffix = 1
            while hist.exists():
                hist = LIBRARY / "_history" / f"{base}_{suffix}.md"
                suffix += 1
            hist.parent.mkdir(exist_ok=True)
            shutil.move(str(dest), hist)
            print(f"  旧版移到 {rel(hist)}")
        data["used_in"] = used
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(write_frontmatter(data, CARD_REQUIRED + ["tags", "used_in"], body), encoding="utf-8")
        print(f"  入库 {rel(dest)}")
    print(f"索引已重建：{build_index()} 张卡")


def cmd_check(a):
    targets = []
    if a.path:
        p = Path(a.path)
        if not p.is_absolute():
            p = (ROOT / a.path) if (ROOT / a.path).exists() else (RUNS / a.path)
        if not p.exists():
            sys.exit(f"找不到：{a.path}")
        targets.append(p.resolve())
    else:
        targets.append(SKILL_DIR)
        targets += list(library_cards())
        targets += all_runs()
    errors, warns = [], []
    for t in targets:
        if t.is_dir() and (t / "SKILL.md").exists():
            e, w = check_skill(t)
        elif t.is_dir():
            e, w = check_run(t)
        else:
            e, w = check_card(t)
        errors += e
        warns += w
    for x in errors:
        print(f"错误  {x}")
    for x in warns:
        print(f"提醒  {x}")
    print(f"检查了 {len(targets)} 项：{len(errors)} 个错误，{len(warns)} 个提醒")
    sys.exit(1 if errors or (getattr(a, "strict", False) and warns) else 0)


def cmd_stats(a):
    tot = {"关卡": 0, "是": 0, "否": 0, "未记": 0}
    by_type: dict = {}
    by_basis = {key: {"关卡": 0, "待答": 0, "是": 0, "否": 0, "未记": 0} for key in ["事前", "回顾", "未知"]}
    runs = []
    for run in all_runs():
        legacy = is_legacy(run)
        gates = legacy_gates(run) if legacy else parse_gates(read(run / LOG))
        c = {"是": 0, "否": 0, "未记": 0}
        for g in gates:
            v = g["fields"].get("改变方向", "")
            pending = g.get("status") == "待答"
            k = "未记" if pending else "是" if v.startswith("是") else "否" if v.startswith("否") else "未记"
            c[k] += 1
            t = g["type"] or "未分类"
            by_type.setdefault(t, {"是": 0, "否": 0, "未记": 0})[k] += 1
            basis = g.get("basis", "未知")
            basis = basis if basis in by_basis else "未知"
            by_basis[basis]["关卡"] += 1
            by_basis[basis]["待答"] += int(pending)
            by_basis[basis][k] += 1
        tot["关卡"] += len(gates)
        for k in c:
            tot[k] += c[k]
        runs.append({"档案": run.name, "结构": "v0.2" if legacy else "v0.3", "关卡": len(gates), **c})
    if a.json:
        print(json.dumps({"合计": tot, "按登记方式": by_basis, "按类型": by_type, "档案": runs,
                          "范围": "改变方向是复盘标注；事前登记、回顾和未知分开，不证明专业质量或因果收益。"}, ensure_ascii=False, indent=2))
        return
    print("| 档案 | 结构 | 关卡 | 改变方向 是/否/未记 |")
    print("|---|---|---|---|")
    for row in runs:
        print(f"| {row['档案']} | {row['结构']} | {row['关卡']} | {row['是']}/{row['否']}/{row['未记']} |")
    print(f"\n合计：{tot['关卡']} 个关卡，改变方向 是 {tot['是']}、否 {tot['否']}、未记 {tot['未记']}")
    if by_type:
        print("按类型：" + "；".join(f"{t} 是{v['是']}/否{v['否']}/未记{v['未记']}" for t, v in sorted(by_type.items())))
    for basis, values in by_basis.items():
        print(f"{basis}：{values['关卡']} 个，待答 {values['待答']}，改变方向 是/否/未记 {values['是']}/{values['否']}/{values['未记']}")
    print("方向变化是复盘标注，不证明质量提高或因果收益；旧记录缺少登记时间/方式的归为未知。")


def cmd_pack(a):
    e, _ = check_skill(SKILL_DIR)
    if e:
        print("\n".join(e))
        sys.exit("技能结构有错误，先修好再导出")
    legal_files = [ROOT / name for name in ("LICENSE", "NOTICE", "ACKNOWLEDGEMENTS.md")]
    missing = [path.name for path in legal_files if not path.is_file()]
    if missing:
        sys.exit("缺少许可与归属文件，请使用完整工具包：" + "、".join(missing))
    DIST.mkdir(exist_ok=True)
    zpath = DIST / "expert-process.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(SKILL_DIR.rglob("*")):
            if f.is_file() and not f.name.startswith("."):
                z.write(f, Path("expert-process") / f.relative_to(SKILL_DIR))
        for path in legal_files:
            z.write(path, Path("expert-process") / path.name)
    _, _, body = split_frontmatter(read(SKILL_DIR / "SKILL.md"))
    body = re.sub(r"\]\(references/([^)]+)\.md\)", r"]（见下文附录：\1）", body)
    parts = [
        "# Expert Process（单文件版）",
        "",
        "> 用在没有命令执行能力的环境（ChatGPT Library、Claude 项目文档）。方法与完整版相同；"
        "四个档案文件（简报、作战图、日志、验收复盘）改为写在对话或项目文档里，eca 命令相关步骤跳过。",
        "",
        body.strip(),
    ]
    for ref in sorted((SKILL_DIR / "references").glob("*.md")):
        parts += ["", "---", "", f"## 附录：{ref.stem}", "", read(ref).strip()]
    for path in legal_files:
        parts += ["", "---", "", f"## 附录：{path.name}", "", read(path).strip()]
    single = DIST / "expert-process_单文件.md"
    single.write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"已导出：{rel(zpath)}（{zpath.stat().st_size} 字节）")
    print(f"已导出：{rel(single)}（{single.stat().st_size} 字节）")


def main(argv=None):
    p = argparse.ArgumentParser(prog="eca", description="Expert Process 工具包本机命令")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("new", help="建档案")
    s.add_argument("slug")
    s.add_argument("--title")
    s.set_defaults(fn=cmd_new)
    s = sub.add_parser("status", help="看档案进度")
    s.add_argument("run", nargs="?")
    s.set_defaults(fn=cmd_status)
    s = sub.add_parser("gate", help="往日志追加一条关卡")
    s.add_argument("run", nargs="?")
    s.add_argument("--id", required=True, help="G1、G2 …")
    s.add_argument("--title", default="", help="新关卡必填；--resolve 时沿用原标题")
    s.add_argument("--resolve", action="store_true", help="收到用户答复后追加结果，不改事前记录")
    s.add_argument("--decision", default="", help="关联决定编号，如 D1")
    s.add_argument("--wait-seconds", type=int, default=None, help="等待提醒秒数；默认不限，超时不自动选择")
    s.add_argument("--type", default="问", help="问 / 确认 / 行业关卡")
    s.add_argument("--gave", default="", help="给了什么")
    s.add_argument("--answer", default="", help="用户答")
    s.add_argument("--counterfactual", default="", help="没问会怎样")
    s.add_argument("--changed", default="", help="改变方向：是 / 否")
    s.add_argument("--writeback", default="", help="回写了哪些文件、哪几条")
    s.set_defaults(fn=cmd_gate)
    s = sub.add_parser("card", help="建卡片：card <process|expert|preference> <id> [run]")
    s.add_argument("type")
    s.add_argument("id")
    s.add_argument("run", nargs="?")
    s.add_argument("--scope", choices=["project", "cross-project"], default="project")
    s.add_argument("--source-ref", default="", help="可选：文件路径、URL或宿主可识别的来源标识，不绑定存储服务")
    s.set_defaults(fn=cmd_card)
    s = sub.add_parser("find", help="在库里查卡片")
    s.add_argument("words", nargs="+")
    s.set_defaults(fn=cmd_find)
    s = sub.add_parser("save", help="卡片入库")
    s.add_argument("run", nargs="?")
    s.set_defaults(fn=cmd_save)
    s = sub.add_parser("index", help="重建索引")
    s.set_defaults(fn=cmd_index)
    s = sub.add_parser("check", help="结构检查")
    s.add_argument("path", nargs="?")
    s.add_argument("--strict", action="store_true", help="提醒也返回失败，用于交付检查")
    s.set_defaults(fn=cmd_check)
    s = sub.add_parser("stats", help="汇总关卡与改变方向")
    s.add_argument("--json", action="store_true", help="输出可复核的分类统计")
    s.set_defaults(fn=cmd_stats)
    s = sub.add_parser("pack", help="导出 zip 与单文件版")
    s.set_defaults(fn=cmd_pack)
    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
