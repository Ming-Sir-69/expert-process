<picture>
  <source media="(prefers-color-scheme: dark)" srcset="readme-assets/cover-zh-dark.png">
  <img src="readme-assets/cover-zh-light.png" alt="Expert Process：共用方法核心、轻量与全量档案、人机关卡和本地卡片库" width="100%">
</picture>

<p align="center">
  <a href="skill/expert-process/SKILL.md">Skill 入口</a> ·
  <a href="skill/expert-process/references/workflow.md">全量工作流</a> ·
  <a href="ACKNOWLEDGEMENTS.md">来源与致谢</a> ·
  <a href="upstream/SOURCES.json">来源元数据</a> ·
  <a href="https://github.com/Ming-Sir-69">作者主页</a>
</p>

<p align="center">
  <a href="LICENSE"><img alt="License Apache-2.0" src="https://img.shields.io/badge/license-Apache--2.0-F6C555?style=flat-square&labelColor=2E2A26"></a>
  <img alt="Python 3.9+" src="https://img.shields.io/badge/python-3.9%2B-6B655C?style=flat-square&labelColor=2E2A26">
  <img alt="Version 0.4" src="https://img.shields.io/badge/version-0.4-6B655C?style=flat-square&labelColor=2E2A26">
  <img alt="CLI standard library" src="https://img.shields.io/badge/CLI-standard%20library-A8A196?style=flat-square&labelColor=2E2A26">
  <img alt="10 reference guides" src="https://img.shields.io/badge/reference%20guides-10-A8A196?style=flat-square&labelColor=2E2A26">
</p>

<p align="center">
  <b>简体中文</b> · <a href="README.en.md">English</a>
</p>

# Expert Process · 面向 Agent 的专业流程、外部档案与人机关卡

Expert Process v0.4 为设计、开发、文档、分析与规划任务提供一份共用方法核心、10 份参考方法、标准库 CLI 和记录模板。Agent 按当前问题的知识缺口与协作需要选用方法，默认轻量处理；长期、多阶段或需要交接时再使用全量档案。项目不绑定模型提供方或外部记忆服务。

## 主要功能

**专业判断、记录形式和执行工具分别选择。** 轻量与全量使用同一完成标准，不以阶段数量、档案数量或卡片数量代替实际交付。

| 用法 | 适用情况 | 记录形式 |
|---|---|---|
| 轻量（默认） | 局部修复、一次性分析、明确的小交付，或只缺一种能力 | 可直接在现有对话或项目中完成，不建档；需要续接时建立一份 `任务.md` 与 `.eca.json` |
| 全量 | 长期、多阶段、依赖复杂，或一份记录难以支撑协作交接 | `1_简报.md`、`2_作战图.md`、`3_日志.md`、`4_验收复盘.md` 四份活文档 |

- **按缺口取用方法**：调研、整合、人机关卡、验收、复盘和技能固化均可独立选用；单个高风险动作只加强相关证据、权限与恢复约束。
- **运行数据留在源码之外**：任务、卡片库和导出物写入显式指定的外部数据目录；CLI 拒绝把运行数据或导出写回工具源码目录。
- **人机关卡保留真实状态**：提问前可登记选项与默认方案，答复以追加事件保存；沉默、取消或超时不会被记为答案或授权。
- **本地卡片按需复用**：流程卡、专家卡和偏好卡保存在同一外部数据根；`cross-project` 只描述适用范围，不触发全局写入或远端同步。
- **两种分发与适配形式**：完整仓库提供 CLI、模板和工具；`pack` 另导出方法 Skill ZIP 与单文件版。ChatGPT 适配为独立纯文本资料。

## 快速开始

要求 Python 3.9 或以上；CLI 只使用标准库。以下命令在仓库根目录运行，`guide` 只读，不创建任务或数据目录：

```sh
git clone https://github.com/Ming-Sir-69/expert-process.git
cd expert-process
python3 cli/eca.py --version
python3 cli/eca.py guide
python3 cli/eca.py guide full
```

也可以把 [Skill 入口](skill/expert-process/SKILL.md) 交给 Agent，由宿主按当前缺口读取参考方法。CLI 不会自动注册全局 Workflow、修改 Agent 规则或连接 Engram。

需要持久保存任务时，显式选择源码目录之外的数据根：

```sh
python3 cli/eca.py --data-dir /path/to/expert-process-data new example --mode lite --title "局部问题"
python3 cli/eca.py --data-dir /path/to/expert-process-data status
python3 cli/eca.py --data-dir /path/to/expert-process-data new migration --mode full --title "多阶段迁移"
```

同一数据根下，`runs/` 保存任务，`library/` 保存可选卡片，`dist/` 保存默认导出物。切换数据根不会搬运或公开旧资料。

## 用法

数据目录按以下优先级选择：命令行 `--data-dir` → 环境变量 `ECA_DATA_DIR` → 用户配置中的 `data_dir` → 平台默认目录。配置文件默认为 `${XDG_CONFIG_HOME:-~/.config}/expert-process/config.json`，也可由 `ECA_CONFIG_FILE` 指定。命令行和环境变量中的相对路径从当前工作目录解析；配置中的相对路径从配置文件所在目录解析。

| 平台 | 默认数据目录 |
|---|---|
| macOS | `~/Library/Application Support/expert-process` |
| Linux | `${XDG_DATA_HOME:-~/.local/share}/expert-process` |
| Windows | `%LOCALAPPDATA%/expert-process` |

<details>
<summary><b>11 个 CLI 子命令</b></summary>

以下命令均可把 `--data-dir` 放在子命令之前；`guide` 不需要写入数据根。

```sh
python3 cli/eca.py guide [lite|full]
python3 cli/eca.py new <slug> --mode lite
python3 cli/eca.py new <slug> --mode full
python3 cli/eca.py status [run]
python3 cli/eca.py gate [run] --id G1 --title … --gave … --counterfactual …
python3 cli/eca.py gate [run] --id G1 --resolve --answer … --changed 是 --writeback …
python3 cli/eca.py card <process|expert|preference> <id> [run]
python3 cli/eca.py find <关键词>
python3 cli/eca.py save [run]
python3 cli/eca.py index
python3 cli/eca.py check [路径] [--strict]
python3 cli/eca.py stats [--json]
python3 cli/eca.py pack
python3 cli/eca.py pack --output-dir /path/to/distribution
```

`new` 默认建立轻量档案。`check --strict` 将结构提醒视为未通过；`stats` 分开统计事前、回顾、未知和待答关卡。完整参数与关卡语义见[关卡规则](skill/expert-process/references/gates.md)。

</details>

`pack` 只包含通用方法及 `LICENSE`、`NOTICE`、`ACKNOWLEDGEMENTS.md`，不包含任务数据、卡片库、CLI、模板或工具脚本。需要命令行自动化时保留完整仓库。ChatGPT 用法是将[专家方法](adapters/chatgpt/专家方法.md)上传到 Library 的共用能力区域，并按需使用[入口指令](adapters/chatgpt/入口指令.txt)；实际可读取范围由当前会话决定。

## 设计与原理

- **共同核心**：先明确目标、约束与完成条件，再补当前缺少的行业依据、专业视角或本人信息。方法结构参考 DisCo / AREX-Skill 的范围、依据、构建与验证思路，经重新组织与裁剪。<sup>[[1]](#参考文献)</sup>
- **阶段与冲突**：全量档案用一张阶段表维护目标、输入、职责、处理、输出、验收、交接和状态；多源冲突处理参考 Skill Seekers 的固定版本并改写，不引入其工作流引擎。<sup>[[2]](#参考文献)</sup>
- **渐进披露**：Skill 入口先选择轻量或全量，再按缺口读取参考文档；技能结构、自由度和结构检查参考 OpenAI skill-creator 的固定版本，检查逻辑以 Python 标准库重新实现。<sup>[[3]](#参考文献)</sup>
- **中断与恢复**：关卡采用保存待决状态、等待外部答复、再追加恢复事件的方式，参考 LangGraph 与 Claude Code 的中断和输入机制，以及 Codex App Server 的用户输入约定；仓库不引入这些运行时。<sup>[[4]](#参考文献)[[5]](#参考文献)[[6]](#参考文献)</sup>
- **可计算检查**：`tools/colormetrics.py` 提供 WCAG 对比度、OKLab/OKLCH 指标和红绿色觉缺陷模拟，分别采用 WCAG、OKLab 与 Machado 等人的公开公式或数值表。<sup>[[7]](#参考文献)[[8]](#参考文献)[[9]](#参考文献)</sup>
- **来源可追溯**：[来源清单](upstream/SOURCES.json)记录 3 个固定上游版本及 352 个文件的路径、大小和哈希，只保存元数据，不附带上游源码。

旧版四文件和 v0.2 档案仍可由 `status`、`check`、`stats` 读取；v0.2 档案不支持用 `gate` 追加新关卡。轻量档案不会被自动转换为全量档案。

## 局限

- CLI 检查档案、卡片和 Skill 的结构，不验证行业判断、专业质量、用户认可或动作授权；模型自评也不等于用户验收。
- `stats` 中的“改变方向”是复盘标注，不证明质量提高或因果收益；仓库没有提供方法效果的量化对照实验。
- 项目不包含模型推理、宿主自动注册、外部记忆服务、MCP 服务或自动上传。ChatGPT 适配不调用本机 CLI，只能使用当前会话实际可见的资料。
- 独立 Skill 包不含 CLI、模板和确定性工具；完整工具包的命令不能据此假定在独立包中可用。
- 来源清单用于归属与研究复核，不表示本项目复制、运行或验证了全部 352 个上游文件。

## 开发

测试使用隔离数据，不操作真实用户任务。结构检查和导出也应使用独立的验证数据根：

```sh
python3 cli/tests/test_eca.py
python3 cli/eca.py --data-dir /path/to/verification-data check --strict
python3 cli/eca.py --data-dir /path/to/verification-data pack --output-dir /path/to/distribution
```

`check --strict` 覆盖 Skill 结构及所选数据根内的档案和卡片；`pack` 会检查许可与归属文件是否齐全。生成物不会自动上传，公开提交前仍需核对新增文件与来源边界。

## 致谢

封面插画由 OpenAI 图像生成模型生成，经本项目处理。

感谢 Python 开源项目提供运行环境与标准库。工作流、卡片结构和检查工具参考 [DisCo / AREX-Skill](https://github.com/VectorSpaceLab/AREX-Skill)、[Skill Seekers](https://github.com/yusufkaraaslan/Skill_Seekers) 与 [OpenAI skill-creator](https://github.com/openai/skills/tree/49f948faa9258a0c61caceaf225e179651397431/skills/.system/skill-creator) 的固定版本。<sup>[[1]](#参考文献)[[2]](#参考文献)[[3]](#参考文献)</sup>

具体贡献、改写范围和上游许可见[致谢与来源](ACKNOWLEDGEMENTS.md)及 [NOTICE](NOTICE)。这些来源不表示上游项目对本项目的认可或背书。

## 参考文献

1. VectorSpaceLab. *DisCo / AREX-Skill*, revision `ac3fe1afa80fb9a09775ecfb2b6cc3ba850a2db6`. <https://github.com/VectorSpaceLab/AREX-Skill/tree/ac3fe1afa80fb9a09775ecfb2b6cc3ba850a2db6>
2. Karaaslan, Y. *Skill Seekers*, revision `5b5d8dfca263fa76e6daae9f292890b311ef36aa`: `complex-merge.yaml`. <https://github.com/yusufkaraaslan/Skill_Seekers/blob/5b5d8dfca263fa76e6daae9f292890b311ef36aa/src/skill_seekers/workflows/complex-merge.yaml>
3. OpenAI. *skill-creator*, revision `49f948faa9258a0c61caceaf225e179651397431`. <https://github.com/openai/skills/tree/49f948faa9258a0c61caceaf225e179651397431/skills/.system/skill-creator>
4. LangChain. *LangGraph documentation: Interrupts*. <https://docs.langchain.com/oss/python/langgraph/interrupts>
5. Anthropic. *Claude Agent SDK: User input*. <https://code.claude.com/docs/en/agent-sdk/user-input>
6. OpenAI. *Codex App Server documentation: User input requests*. <https://learn.chatgpt.com/docs/app-server>
7. W3C. *Web Content Accessibility Guidelines (WCAG) 2.2: Contrast ratio*. <https://www.w3.org/TR/WCAG22/#dfn-contrast-ratio>
8. Ottosson, B. *A perceptual color space for image processing*. <https://bottosson.github.io/posts/oklab/>
9. Machado, G. M., Oliveira, M. M., & Fernandes, L. A. F. (2009). A Physiologically-based Model for Simulation of Color Vision Deficiency. *IEEE Transactions on Visualization and Computer Graphics*, 15(6), 1291–1298. 数值表见作者页面 Table 1，severity 1.0。<https://www.inf.ufrgs.br/~oliveira/pubs_files/CVD_Simulation/CVD_Simulation.html>

## 相关研究

以下文献用于方法比较与背景阅读，不表示本仓库依据这些文献实现，也不表示仓库包含相应的模型训练或推理机制。

1. Shinn, N., Cassano, F., Berman, E., Gopinath, A., Narasimhan, K., & Yao, S. (2023). Reflexion: Language Agents with Verbal Reinforcement Learning. *NeurIPS 2023*. <https://arxiv.org/abs/2303.11366>。将任务反馈整理为后续可读取的反思，对应本项目的复盘与续接讨论。
2. Madaan, A., et al. (2023). Self-Refine: Iterative Refinement with Self-Feedback. *NeurIPS 2023*. <https://arxiv.org/abs/2303.17651>。生成、反馈与修改的循环，对应按需验收和修订；本项目不内置该推理循环。
3. Shankar, S., Zamfirescu-Pereira, J. D., Hartmann, B., Parameswaran, A., & Arawjo, I. (2024). Who Validates the Validators? Aligning LLM-Assisted Evaluation of LLM Outputs with Human Preferences. *UIST '24*. <https://doi.org/10.1145/3654777.3676450>。人工评审中形成评价标准，对应本项目区分结构检查、专业判断与本人验收。
4. Amershi, S., Cakmak, M., Knox, W. B., & Kulesza, T. (2014). Power to the People: The Role of Humans in Interactive Machine Learning. *AI Magazine*, 35(4), 105–120. <https://doi.org/10.1609/aimag.v35i4.2513>。人在交互过程中的信息与决定作用，对应本项目的人机关卡；本项目不是交互式机器学习系统。

## 仓库结构

| 位置 | 内容 |
|---|---|
| `skill/expert-process/` | Skill 入口与 10 份参考方法 |
| `cli/eca.py` | 档案、关卡、卡片、检查和导出命令 |
| `cli/tests/test_eca.py` | 使用隔离数据的行为回归测试 |
| `templates/` | 轻量档案、全量档案与三类卡片模板 |
| `tools/colormetrics.py` | 对比度、OKLab/OKLCH 与色觉缺陷模拟 |
| `adapters/chatgpt/` | Library 纯文本资料与入口指令 |
| `upstream/SOURCES.json` | 固定上游版本与文件哈希元数据 |
| `LICENSE`、`NOTICE`、`ACKNOWLEDGEMENTS.md` | 许可、上游归属与改写范围 |
| `readme-assets/` | README 封面与署名资源 |

---

文档维护：<picture><source media="(prefers-color-scheme: dark)" srcset="readme-assets/em-logo-dark.svg"><img src="readme-assets/em-logo-light.svg" alt="EM" height="13"></picture> <b>EricMingle69</b> · <a href="https://github.com/Ming-Sir-69">Ming-Sir-69</a><br>
代码、文字与自有图形以 [Apache License 2.0](LICENSE) 发布；上游内容的归属与许可见 [NOTICE](NOTICE)。
