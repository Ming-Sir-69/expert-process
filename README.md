# Expert Process｜专家流程工具包

状态：v0.3（2026-10-21，按不确定性分流，支持统一模块接口和本地知识卡片）。
面向设计、开发、文档、分析与规划的轻量工作流：模型负责专业判断，本地CLI负责记录、检查与导出。Python 3.9+，CLI仅用标准库，不绑定模型提供方或外部记忆服务。

## 一句话

**Agent 用流程做行业适配，人提供偏好与视角。** 每个决定先分类：可计算的**算**、行业惯例**查**（都由 Agent 完成），口味和只有本人知道的情境**问**、不可逆的**确认**（由人决定）。行业知识沉淀成流程卡、专家卡，经验与偏好先服务当前任务和项目，是否值得跨项目提炼由Agent结合证据与复用价值判断。工具不要求接入外部记忆服务。模块和阶段采用统一七字段接口。

## 快速开始

```bash
git clone https://github.com/Ming-Sir-69/expert-process.git
cd expert-process
python3 cli/eca.py check --strict
python3 cli/eca.py new example --title "示例任务"
python3 cli/eca.py status
```

把[Skill入口](skill/expert-process/SKILL.md)交给Agent阅读，然后按本次任务填写档案。所有CLI命令都在工具包根目录运行；`runs/`与`library/`在使用时生成，并默认被Git忽略。仓库不附带真实用户的偏好、任务记录或资产。

## 怎么用

| 场景 | 做法 |
|---|---|
| 能执行命令的Agent，包括本地Codex、Claude Code或已有远程执行连接 | 读`skill/expert-process/SKILL.md`，从工具包根目录调用CLI |
| 只安装Skill的环境 | 先运行`python3 cli/eca.py pack`，安装生成的`dist/expert-process.zip`；CLI自动化仍需完整工具包 |
| 无命令执行能力的对话或项目文档 | 运行`pack`后上传`dist/expert-process_单文件.md`，按小节维护档案 |

导出物包含通用方法和许可说明，不包含本地任务资料。ZIP不包含CLI、模板或tools；需要自动化时保留完整仓库。`dist/`为本地生成目录，不提交生成物。

命令（只用 Python 标准库）：

```bash
python3 cli/eca.py new <slug> --title "任务名"   # 建档案：1_简报 2_作战图 3_日志 4_验收复盘
python3 cli/eca.py status [run]                 # 看进度（默认最近改过的档案）
python3 cli/eca.py gate [run] --id G1 --title … --gave … --counterfactual … # 提问前登记
python3 cli/eca.py gate [run] --id G1 --resolve --answer … --changed 是 --writeback … # 答复后追加
python3 cli/eca.py card <process|expert|preference> <id>   # 建卡片
python3 cli/eca.py stats [--json]               # 分开事前/回顾/未知和待答
python3 tools/colormetrics.py <色> <相邻色> [<避开色>]   # 对比度、色弱、色差
python3 cli/eca.py find <关键词>                 # 查库
python3 cli/eca.py save [run]                   # 卡片入库
python3 cli/eca.py check [路径] [--strict]       # 接口、结构与待答检查
python3 cli/eca.py pack                         # 导出 zip 与单文件版
python3 cli/tests/test_eca.py                   # 冒烟测试
```

## 目录

| 路径 | 是什么 | 运行时会用到吗 |
|---|---|---|
| `skill/expert-process/` | 技能本体：SKILL.md + 8 份参考（含workflow.md统一接口与gates.md关卡规则） | 是 |
| `tools/` | 确定性检查脚本（第一个：colormetrics.py），专家卡可引用 | 是 |
| `cli/` | eca 命令与测试 | 是（有命令执行时） |
| `templates/` | 档案模板与卡片模板 | 由 eca 调用 |
| `library/` | 使用时生成的本地卡片库与索引，Git忽略 | 是（先查库） |
| `runs/` | 使用时生成的任务档案，Git忽略 | 是 |
| `dist/` | 导出物，可随时用 `pack` 重新生成 | 分发用 |
| `upstream/SOURCES.json` | 参考来源的固定提交、原路径及逐文件哈希；不附带上游整库 | 否 |

## 当前入口

方法从[Skill](skill/expert-process/SKILL.md)进入；模块和阶段结构见[接口与交接](skill/expert-process/references/workflow.md)，知识归属见[卡片与适用范围](skill/expert-process/references/cards.md)。当前实现以这些指南、CLI和模板为准。

## 验收边界

结构检查、宿主自动选中和专业水准提升分别判断。回归测试覆盖CLI的结构和状态迁移，不证明宿主提问面板行为或跨领域专业收益。

运行本地检查：

```bash
python3 cli/tests/test_eca.py
python3 cli/eca.py check --strict
python3 cli/eca.py pack
```

测试只在临时副本操作。生成文件和本地档案不会自动上传；公开提交前仍需检查自己的新增文件。

## 许可与致谢

本项目采用[Apache License 2.0](LICENSE)。感谢[DisCo / AREX-Skill](https://github.com/VectorSpaceLab/AREX-Skill)、[Skill Seekers](https://github.com/yusufkaraaslan/Skill_Seekers)和[OpenAI skill-creator](https://github.com/openai/skills/tree/49f948faa9258a0c61caceaf225e179651397431/skills/.system/skill-creator)提供的方法与结构参考。

各项目具体贡献、固定版本及改写范围见[致谢](ACKNOWLEDGEMENTS.md)；相关上游归属和许可见[NOTICE](NOTICE)。本项目不代表上述项目，也不依赖其运行时。

## 上游版本

[来源清单](upstream/SOURCES.json)列出研究时核对的352个文件及固定版本。公开仓库只提供这份来源元数据，不附带上游源码；运行本工具无需先下载这些上游项目。该清单不表示本项目复制或运行了全部列出文件。
