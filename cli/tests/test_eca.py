#!/usr/bin/env python3
"""eca 冒烟测试（v0.3）：在临时副本里走一遍 new → status → gate → check → card → save → find → stats → pack。
只证明命令能跑、规则生效，不证明工具包能提高专业水准。"""
import os
import json
import datetime as dt
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile
from unittest import mock
from types import SimpleNamespace
from pathlib import Path

SRC = Path(__file__).resolve().parents[2]


def run(root, *args, ok=True):
    r = subprocess.run([sys.executable, str(root / "cli" / "eca.py"), *args],
                       capture_output=True, text=True)
    if ok and r.returncode != 0:
        raise AssertionError(f"eca {' '.join(args)} 失败：\n{r.stdout}\n{r.stderr}")
    return r


class EcaSmoke(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for d in ("cli", "skill", "templates", "tools"):
            shutil.copytree(SRC / d, self.tmp / d, ignore=shutil.ignore_patterns("tests", "__pycache__"))
        for name in ("LICENSE", "NOTICE", "ACKNOWLEDGEMENTS.md"):
            shutil.copyfile(SRC / name, self.tmp / name)
        for sub in ("processes", "experts", "preferences"):
            (self.tmp / "library" / sub).mkdir(parents=True)
        (self.tmp / "runs").mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def new_run(self, slug="测试 任务"):
        run(self.tmp, "new", slug, "--title", "测试任务")
        return max((self.tmp / "runs").iterdir(), key=lambda p: p.stat().st_mtime)

    def test_new_and_living_docs(self):
        run_dir = self.new_run()
        for name in ("1_简报.md", "2_作战图.md", "3_日志.md", "4_验收复盘.md"):
            self.assertTrue((run_dir / name).exists(), name)
        self.assertTrue((run_dir / "1_简报.md").read_text(encoding="utf-8").startswith("# 简报：测试任务"))
        self.assertTrue((run_dir / "outputs" / "drafts").is_dir())
        self.assertFalse(list(run_dir.rglob(".keep")))
        st = run(self.tmp, "status").stdout
        self.assertIn("待填", st)
        self.assertIn("0 条记录", st)

    def test_gate_and_check_warnings(self):
        run_dir = self.new_run()
        # 关卡缺回写 → 提醒；日志已开始而简报没填 → 提醒
        run(self.tmp, "gate", "--id", "G1", "--title", "简报确认", "--decision", "D1", "--gave", "三个选项", "--answer", "选 B",
            "--counterfactual", "会选 A", "--changed", "是")
        log = (run_dir / "3_日志.md").read_text(encoding="utf-8")
        self.assertIn("### G1 简报确认（问）", log)
        self.assertIn("- 回写：（待填）", log)
        r = run(self.tmp, "gate", "--id", "G1", "--title", "重复", ok=False)
        self.assertNotEqual(r.returncode, 0)
        out = run(self.tmp, "check", str(run_dir)).stdout
        self.assertIn("关卡 G1 缺 回写", out)
        self.assertIn("活文档没有跟上", out)
        # "问"类决定没有答案 → 提醒；答了就不提醒
        plan = run_dir / "2_作战图.md"
        text = plan.read_text(encoding="utf-8").replace("| D1 | （待填） | | | | |",
                                                         "| D1 | 整体方向 | 问 | 1 | 关卡 | 未定 |\n| D2 | 对比度 | 算 | 2 | 脚本 | 已定 |")
        plan.write_text(text, encoding="utf-8")
        out = run(self.tmp, "check", str(run_dir)).stdout
        self.assertIn("D1「整体方向」是\"问\"类", out)
        self.assertNotIn("D2", out)
        plan.write_text(text.replace("| 关卡 | 未定 |", "| 关卡 | 已答 G1 |"), encoding="utf-8")
        self.assertNotIn("D1", run(self.tmp, "check", str(run_dir)).stdout)
        st = run(self.tmp, "status").stdout
        self.assertIn("关卡 1 个", st)
        self.assertIn("问 1 条，待答 0 条", st)
        stats = run(self.tmp, "stats").stdout
        self.assertIn("合计：1 个关卡，改变方向 是 1", stats)

    def test_status_picks_most_recent_run(self):
        a = self.new_run("aaa")
        b = self.new_run("zzz")
        old = time.time() - 3600
        for p in b.rglob("*"):
            os.utime(p, (old, old))
        (a / "3_日志.md").write_text("# 日志\n\n### 今天\n- 产出：x\n", encoding="utf-8")
        self.assertIn(a.name, run(self.tmp, "status").stdout)

    def test_cards_save_find(self):
        run_dir = self.new_run()
        run(self.tmp, "card", "expert", "logo-designer")
        card = run_dir / "cards" / "logo-designer.md"
        self.assertTrue(card.exists())
        self.assertNotEqual(run(self.tmp, "save", ok=False).returncode, 0)  # 未填完不能入库
        card.write_text(
            "---\ntype: expert\nid: logo-designer\ntitle: 标识设计师\ndomain: 品牌设计\n"
            "tags: [logo, 品牌]\nupdated: 2026-10-20\nconfidence: 中\n---\n\n## 考虑点\n- [ ] 小尺寸可辨认\n",
            encoding="utf-8")
        pref = run_dir / "cards" / "someone-visual.md"
        pref.write_text(
            "---\ntype: preference\nid: someone-visual\ntitle: 某人的视觉偏好\ndomain: 视觉\n"
            "tags: [审美]\nupdated: 2026-10-21\nconfidence: 中\n---\n\n## 偏好条目\n"
            "| 条目 | 状态 | 日期 | 来源 |\n|---|---|---|---|\n| 喜欢手稿感 | 有效 | 2020-01-01 | G1 |\n| 不要灰 | 很确定 | 2026-10-21 | G1 |\n",
            encoding="utf-8")
        out = run(self.tmp, "check", str(run_dir)).stdout
        self.assertIn("天未确认", out)
        self.assertIn("状态应为", out)
        out = run(self.tmp, "save").stdout
        self.assertIn("入库", out)
        self.assertTrue((self.tmp / "library" / "preferences" / "someone-visual.md").exists())
        lib = self.tmp / "library" / "experts" / "logo-designer.md"
        self.assertIn("used_in: [", lib.read_text(encoding="utf-8"))
        run(self.tmp, "save")  # 再存一次：旧版进 _history，used_in 不重复
        self.assertEqual(len(list((self.tmp / "library" / "_history").glob("logo-designer_*.md"))), 1)
        self.assertEqual(lib.read_text(encoding="utf-8").count(run_dir.name), 1)
        self.assertIn("[偏好卡] someone-visual", run(self.tmp, "find", "手稿").stdout)
        self.assertIn("没有匹配", run(self.tmp, "find", "不存在的词").stdout)
        index = (self.tmp / "library" / "INDEX.md").read_text(encoding="utf-8")
        self.assertIn("## 偏好卡（1）", index)

    def test_legacy_run_still_readable(self):
        legacy = self.tmp / "runs" / "2026-10-20_old"
        legacy.mkdir()
        for name in ("00_定位.md", "01_流程.md", "02_专家.md", "03_整合.md", "04_执行.md", "05_验收.md", "06_复盘.md"):
            (legacy / name).write_text("# x\n", encoding="utf-8")
        (legacy / "关卡记录.md").write_text("## G1 简报\n## G2 方向\n", encoding="utf-8")
        self.assertIn("v0.2 旧结构", run(self.tmp, "status", str(legacy)).stdout)
        run(self.tmp, "check", str(legacy))
        self.assertIn("| 2026-10-20_old | v0.2 | 2 | 0/0/2 |", run(self.tmp, "stats").stdout)
        self.assertNotEqual(run(self.tmp, "gate", str(legacy), "--id", "G3", "--title", "x", ok=False).returncode, 0)

    def test_skill_check_and_pack(self):
        run(self.tmp, "check", "skill/expert-process")
        run(self.tmp, "pack")
        self.assertTrue((self.tmp / "dist" / "expert-process.zip").exists())
        single = (self.tmp / "dist" / "expert-process_单文件.md").read_text(encoding="utf-8")
        self.assertIn("附录：gates", single)
        self.assertIn("按不确定性分流", single)
        with zipfile.ZipFile(self.tmp / "dist/expert-process.zip") as package:
            self.assertIsNone(package.testzip())
            for name in ("LICENSE", "NOTICE", "ACKNOWLEDGEMENTS.md"):
                self.assertEqual(package.read("expert-process/" + name), (self.tmp / name).read_bytes())
                self.assertIn((self.tmp / name).read_text().strip(), single)
            self.assertFalse(any("runs/" in name or "library/" in name for name in package.namelist()))

    def test_pack_requires_distribution_notices(self):
        (self.tmp / "LICENSE").unlink()
        result = run(self.tmp, "pack", ok=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("LICENSE", result.stderr)
        self.assertFalse((self.tmp / "dist/expert-process.zip").exists())

    def test_color_metrics_uses_arguments_and_generic_help(self):
        tool = self.tmp / "tools/colormetrics.py"
        help_result = subprocess.run([sys.executable, str(tool)], capture_output=True, text=True)
        self.assertEqual(help_result.returncode, 0)
        self.assertIn("usage:", help_result.stdout)
        result = subprocess.run([sys.executable, str(tool), "000000", "FFFFFF"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("21.00:1", result.stdout)
        bad = subprocess.run([sys.executable, str(tool), "invalid", "FFFFFF"], capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2)
        self.assertNotIn("Traceback", bad.stderr)

    def test_bad_skill_is_rejected(self):
        md = self.tmp / "skill" / "expert-process" / "SKILL.md"
        md.write_text(md.read_text(encoding="utf-8").replace("name: expert-process", "name: Expert_Process"),
                      encoding="utf-8")
        r = run(self.tmp, "check", "skill/expert-process", ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("name 只能用", r.stdout)

    def test_bad_card_fields(self):
        run_dir = self.new_run("x")
        (run_dir / "cards").mkdir(exist_ok=True)
        (run_dir / "cards" / "bad.md").write_text(
            "---\ntype: other\nid: Bad_ID\ntitle: t\ndomain: d\nupdated: 20261020\nconfidence: 很高\n---\n",
            encoding="utf-8")
        r = run(self.tmp, "check", str(run_dir), ok=False)
        for msg in ("type 只能是", "id 只能用", "confidence 只能是", "updated 要写成"):
            self.assertIn(msg, r.stdout)

    def test_gate_checkpoint_and_resume_preserves_proposal(self):
        task = self.new_run("checkpoint")
        opened = run(self.tmp, "gate", str(task), "--id", "G1", "--title", "报告读者", "--decision", "D1",
                     "--gave", "管理层/工程团队", "--counterfactual", "默认管理层版", "--wait-seconds", "0")
        self.assertNotIn("回写为空", opened.stdout)
        before = (task / "3_日志.md").read_text()
        status = run(self.tmp, "status", str(task)).stdout
        self.assertIn("待用户答复", status)
        self.assertIn("待答关卡   1 个", status)
        stats = json.loads(run(self.tmp, "stats", "--json").stdout)
        self.assertEqual(stats["按登记方式"]["事前"]["待答"], 1)
        self.assertEqual(stats["合计"]["是"], 0)
        self.assertNotEqual(run(self.tmp, "check", str(task), "--strict", ok=False).returncode, 0)
        bad = run(self.tmp, "gate", str(task), "--id", "G1", "--resolve", "--answer", "工程团队版",
                  "--counterfactual", "伪造的事前方案", ok=False)
        self.assertNotEqual(bad.returncode, 0)
        self.assertEqual((task / "3_日志.md").read_text(), before)
        run(self.tmp, "gate", str(task), "--id", "G1", "--resolve", "--answer", "工程团队版",
            "--changed", "是", "--writeback", "简报受众与D1已更新")
        after = (task / "3_日志.md").read_text()
        self.assertTrue(after.startswith(before.rstrip("\n")))
        self.assertEqual(after.split("-->")[-1].count("### G1"), 2)
        stats = json.loads(run(self.tmp, "stats", "--json").stdout)
        self.assertEqual(stats["合计"]["关卡"], 1)
        self.assertEqual(stats["按登记方式"]["事前"]["是"], 1)
        self.assertEqual(stats["按登记方式"]["事前"]["待答"], 0)
        self.assertNotEqual(run(self.tmp, "gate", str(task), "--id", "G1", "--resolve", "--answer", "再改一次", ok=False).returncode, 0)

    def test_retrospective_unknown_and_pending_are_separate(self):
        task = self.new_run("classification")
        run(self.tmp, "gate", str(task), "--id", "G1", "--title", "事后复盘", "--gave", "A/B",
            "--answer", "B", "--counterfactual", "认为会选A", "--changed", "是", "--writeback", "复盘")
        run(self.tmp, "gate", str(task), "--id", "G2", "--title", "默认等待", "--gave", "A/B", "--counterfactual", "A")
        with (task / "3_日志.md").open("a") as log:
            log.write("\n### G3 无时间元数据（问）— 2026-10-21\n- 给了：A/B\n- 答：A\n- 改变方向：否\n")
        stats = json.loads(run(self.tmp, "stats", "--json").stdout)
        self.assertEqual(stats["按登记方式"]["回顾"]["是"], 1)
        self.assertEqual(stats["按登记方式"]["未知"]["否"], 1)
        self.assertEqual(stats["按登记方式"]["事前"]["待答"], 1)
        self.assertIn("- 等待秒数：不限", (task / "3_日志.md").read_text())
        old = (task / "3_日志.md").read_text()
        self.assertNotEqual(run(self.tmp, "gate", str(task), "--id", "G4", "--title", "没有回答",
                                "--changed", "是", ok=False).returncode, 0)
        self.assertEqual((task / "3_日志.md").read_text(), old)

    def test_fake_answer_and_unapproved_assumption_stay_unresolved(self):
        task = self.new_run("decision")
        plan = task / "2_作战图.md"
        content = plan.read_text().replace("| D1 | （待填） | | | | |", "| D1 | 受众 | 问 | 1 | 提问 | 已答 G99 |")
        plan.write_text(content)
        self.assertIn('D1「受众」是"问"类', run(self.tmp, "check", str(task)).stdout)
        self.assertIn("待答 1 条", run(self.tmp, "status", str(task)).stdout)
        plan.write_text(content.replace("已答 G99", "假设管理层"))
        self.assertIn('D1「受众」是"问"类', run(self.tmp, "check", str(task)).stdout)
        brief = task / "1_简报.md"
        brief.write_text(brief.read_text().replace("自主推进：未授权", "自主推进：已授权"))
        self.assertNotIn('D1「受众」是"问"类', run(self.tmp, "check", str(task)).stdout)
        plan.write_text(content.replace("| 问 |", "| 确认 |").replace("已答 G99", "假设同意"))
        self.assertIn('D1「受众」是"确认"类', run(self.tmp, "check", str(task)).stdout)

    def test_completed_phase_needs_inputs_and_acceptance(self):
        task = self.new_run("handoff")
        plan = task / "2_作战图.md"
        plan.write_text("# 方案\n\n## 阶段交接\n\n| 阶段 | 目标 | 输入 | 职责 | 处理 | 输出 | 验收 | 交接 | 状态 |\n"
                        "|---|---|---|---|---|---|---|---|---|\n"
                        "| 范围界定 | 明确目标 | | Agent | 核对约束 | 简报 | 标准明确 | 调研 | 已完成 |\n")
        self.assertIn("已完成却缺 输入", run(self.tmp, "check", str(task)).stdout)

    def test_preference_scope_and_sources_are_provider_neutral(self):
        task = self.new_run("scope")
        run(self.tmp, "card", "preference", "project-style", str(task))
        local = task / "cards/project-style.md"
        self.assertIn("scope: project", local.read_text())
        run(self.tmp, "card", "preference", "reusable-style", str(task), "--scope", "cross-project")
        reusable = task / "cards/reusable-style.md"
        self.assertIn("storage: workspace", reusable.read_text())
        self.assertIn("## 偏好条目", reusable.read_text())
        self.assertNotIn("source_ref:", reusable.read_text())
        run(self.tmp, "card", "preference", "global-style", str(task), "--scope", "cross-project", "--source-ref", "notes/preferences.md")
        ref = task / "cards/global-style.md"
        self.assertIn("storage: reference", ref.read_text())
        self.assertNotIn("## 偏好条目", ref.read_text())
        ref.write_text("---\ntype: preference\nid: global-style\ntitle: 来源引用\ndomain: 文档\nupdated: 2026-10-21\nconfidence: 中\nscope: cross-project\nstorage: reference\nsource_ref: notes/preferences.md\n---\n\n## 来源\n普通文件引用，不依赖外部服务。\n")
        local.unlink()  # 隔离夹具只入库一个引用。
        reusable.unlink()
        run(self.tmp, "save", str(task))
        target = self.tmp / "library/preferences/global-style.md"
        before = target.read_text()
        ref.write_text(ref.read_text().replace("scope: cross-project\n", ""))
        self.assertNotEqual(run(self.tmp, "save", str(task), ok=False).returncode, 0)
        self.assertEqual(target.read_text(), before)
        ref.write_text(ref.read_text().replace("storage: reference", "scope: project\nstorage: workspace"))
        run(self.tmp, "save", str(task))
        self.assertIn("scope: project", target.read_text())
        history = list((self.tmp / "library/_history").glob("global-style_*.md"))
        self.assertTrue(any("scope: cross-project" in path.read_text() for path in history))

    def test_module_contract_rejects_missing_input(self):
        module = self.tmp / "skill/expert-process/references/research.md"
        module.write_text("\n".join(line for line in module.read_text().splitlines() if not line.startswith("| 输入 |")) + "\n")
        result = run(self.tmp, "check", "skill/expert-process", ok=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("模块接口缺 输入", result.stdout)

    def test_missing_phase_table_cannot_pass_strict_check(self):
        task = self.new_run("missing-phase-table")
        plan = task / "2_作战图.md"
        text = plan.read_text()
        first, last = text.index("## 阶段交接"), text.index("## 决策登记")
        plan.write_text(text[:first] + text[last:])
        result = run(self.tmp, "check", str(task), "--strict", ok=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("缺少阶段交接表", result.stdout)

    def test_unrelated_or_wrong_type_gate_does_not_answer_decision(self):
        task = self.new_run("gate-binding")
        run(self.tmp, "gate", str(task), "--id", "G1", "--title", "配色选择", "--decision", "D2",
            "--gave", "A/B", "--answer", "B", "--counterfactual", "A", "--changed", "是", "--writeback", "D2")
        plan = task / "2_作战图.md"
        text = plan.read_text().replace("| D1 | （待填） | | | | |", "| D1 | 删除 | 确认 | 1 | G1 | 已答 G1 |")
        plan.write_text(text)
        self.assertIn('D1「删除」是"确认"类', run(self.tmp, "check", str(task)).stdout)
        run(self.tmp, "gate", str(task), "--id", "G2", "--title", "删除确认", "--decision", "D1",
            "--type", "确认", "--gave", "列出的文件", "--answer", "本人明确允许这些文件", "--counterfactual", "等待", "--changed", "未知", "--writeback", "D1")
        plan.write_text(text.replace("| G1 | 已答 G1 |", "| G2 | 已答 G2 |"))
        self.assertNotIn('D1「删除」是"确认"类', run(self.tmp, "check", str(task)).stdout)

    def test_same_timestamp_saves_preserve_every_previous_version(self):
        task = self.new_run("history")
        card = task / "cards/history-example.md"
        spec = importlib.util.spec_from_file_location("eca_history_test", self.tmp / "cli/eca.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        fixed = dt.datetime(2026, 10, 21, 12, 0, 0)
        with mock.patch.object(module.dt, "datetime") as clock:
            clock.now.return_value = fixed
            for version in ("VERSION_ONE", "VERSION_TWO", "VERSION_THREE"):
                card.write_text("---\ntype: expert\nid: history-example\ntitle: 历史保留\ndomain: 文档\nupdated: 2026-10-21\nconfidence: 中\n---\n\n" + version + "\n")
                module.cmd_save(SimpleNamespace(run=str(task)))
        history = list((self.tmp / "library/_history").glob("history-example_*.md"))
        self.assertEqual(len(history), 2)
        saved = "\n".join(path.read_text() for path in history)
        self.assertIn("VERSION_ONE", saved)
        self.assertIn("VERSION_TWO", saved)
        self.assertIn("VERSION_THREE", (self.tmp / "library/experts/history-example.md").read_text())

    def test_reusable_candidate_can_stay_local_without_memory_service(self):
        task = self.new_run("local-reuse")
        run(self.tmp, "card", "preference", "report-order", str(task), "--scope", "cross-project")
        card = task / "cards/report-order.md"
        card.write_text("---\ntype: preference\nid: report-order\ntitle: 可复用候选\ndomain: 报告\nupdated: 2026-10-21\nconfidence: 低\nscope: cross-project\nstorage: workspace\n---\n\n"
                        "## 适用范围\n跨项目候选，尚未发布到全局；合成夹具。\n\n## 偏好条目\n"
                        "| 条目 | 状态 | 日期 | 来源 |\n|---|---|---|---|\n| 先列异常 | 有效 | 2026-10-21 | 两个合成任务 |\n")
        run(self.tmp, "check", str(card), "--strict")
        run(self.tmp, "save", str(task))
        target = self.tmp / "library/preferences/report-order.md"
        self.assertIn("storage: workspace", target.read_text())
        self.assertNotIn("source_ref:", target.read_text())
        self.assertIn("report-order", run(self.tmp, "find", "先列异常").stdout)
        run(self.tmp, "stats", "--json")
        run(self.tmp, "pack")

    def test_legacy_preference_does_not_require_new_scope_metadata(self):
        task = self.tmp / "runs/legacy-preference"
        task.mkdir()
        for filename in ("00_定位.md", "01_流程.md", "02_专家.md", "03_整合.md", "04_执行.md", "05_验收.md", "06_复盘.md"):
            (task / filename).write_text("# 历史原件\n")
        (task / "cards").mkdir()
        (task / "cards/old-pref.md").write_text("---\ntype: preference\nid: old-pref\ntitle: 旧项目约定\ndomain: 本项目\nupdated: 2026-10-21\nconfidence: 中\n---\n\n仅作旧项目上下文。\n")
        result = run(self.tmp, "check", str(task), "--strict")
        self.assertNotIn("缺 scope", result.stdout)

    def test_empty_phase_template_cannot_be_completed_by_status_only(self):
        task = self.new_run("empty-phase")
        plan = task / "2_作战图.md"
        text = plan.read_text()
        self.assertNotIn("## 阶段 × 专家", text)
        self.assertNotIn("| 简报 | 明确目标与约束", text)
        plan.write_text(text.replace("| 未开始 |", "| 已完成 |"))
        result = run(self.tmp, "check", str(task), "--strict", ok=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("已完成却缺", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
