# Expert Process｜专家流程工具包

v0.4：面向电脑端的Workflow／CLI，共用一份方法核心，默认轻量，按需要使用全量工作流。适用于设计、开发、文档、分析与规划。Python 3.9+，CLI仅用标准库，不绑定模型提供方或外部记忆服务。

**Agent按当前问题选择最小充分的方法，承担专业取舍；用户提供其专属信息和必要授权。** 专业判断、记录形式和执行工具分别选择，不为流程完整额外建档、调研或写卡。

## 快速开始

```bash
git clone https://github.com/Ming-Sir-69/expert-process.git
cd expert-process
python3 cli/eca.py guide
```

`guide`默认展示共同核心和轻量用法，只读输出，不创建任务或数据目录。也可以把[Skill入口](skill/expert-process/SKILL.md)交给Agent，按需读取参考方法。

| 用法 | 何时用 | 怎么用 |
|---|---|---|
| 轻量（默认） | 小问题、局部修复、一次性分析，或只缺一种能力 | `guide lite`；可在现有对话或项目中直接完成，不建档 |
| 轻量续接 | 需要保存当前目标、重要选择与未决事项 | `new <slug> --mode lite`；一份`任务.md`和`.eca.json` |
| 全量 | 长期、多阶段、依赖复杂，或需要协作交接 | `guide full`、`new <slug> --mode full`；四份活文档，按实际需要组织阶段 |

两种用法采用同一方法与完成标准。轻量不代表省略必要检查，全量也不要求用完所有模块。单个高风险动作只加强相关约束，不自动升级整套流程。CLI只提供方法和记录能力，取舍由Agent完成。

## 数据留在工具目录之外

工具仓库只维护源码、方法、模板、测试和许可。任务、过程稿、关卡、私人卡片和导出都写到**外部数据目录**，不在工具仓库内生成运行资料。

数据目录按以下优先级选择：

1. 命令行`--data-dir`。
2. 环境变量`ECA_DATA_DIR`。
3. 用户配置中的`data_dir`。
4. 平台默认用户数据目录。

配置默认位于`${XDG_CONFIG_HOME:-~/.config}/expert-process/config.json`，也可用`ECA_CONFIG_FILE`指定。配置只需一个`data_dir`字段。命令行和环境变量的相对目录从当前工作目录解析；配置中的相对目录从配置文件所在目录解析。

| 平台 | 默认数据目录 |
|---|---|
| macOS | `~/Library/Application Support/expert-process` |
| Linux | `${XDG_DATA_HOME:-~/.local/share}/expert-process` |
| Windows | `%LOCALAPPDATA%/expert-process` |

同一数据目录下按`runs/`保存任务、`library/`保存可选复用卡片、`dist/`保存导出物。项目专属资料可以指定该项目的外部运行区；跨项目标记不会自动向全局或外部服务写入。卡片的相对`source_ref`从数据根解析。

```bash
python3 cli/eca.py --data-dir /path/to/project-state new example --mode lite --title "局部问题"
python3 cli/eca.py --data-dir /path/to/project-state status
python3 cli/eca.py --data-dir /path/to/project-state new migration --mode full --title "多阶段迁移"
```

CLI拒绝将运行数据或导出写入工具源码目录。切换数据目录只改变资料位置，不赋予Agent额外权限，也不会自动搬运或公开旧资料。

## 常用命令

以下命令均在工具包根目录运行，可在子命令前加`--data-dir`：

```bash
python3 cli/eca.py guide [lite|full]            # 只读方法；默认lite
python3 cli/eca.py new <slug> --mode lite       # 可选的单文件续接记录；默认模式
python3 cli/eca.py new <slug> --mode full       # 建四份活文档
python3 cli/eca.py status [run]                # 当前进度与待答关卡
python3 cli/eca.py gate [run] --id G1 --title … --gave … --counterfactual …
python3 cli/eca.py gate [run] --id G1 --resolve --answer … --changed 是 --writeback …
python3 cli/eca.py card <process|expert|preference> <id> [run]
python3 cli/eca.py find <关键词>                # 查可选卡片库
python3 cli/eca.py save [run]                  # 将有复用价值的卡片入库
python3 cli/eca.py stats [--json]              # 区分事前／回顾／未知和待答
python3 cli/eca.py check [路径] [--strict]      # 按实际模式检查结构与状态
python3 cli/eca.py pack                        # 导出到外部数据目录的dist/
python3 cli/eca.py pack --output-dir /path/to/distribution
```

完整关卡用法见[关卡规则](skill/expert-process/references/gates.md)。问题没有真正出现就无需造关卡，关卡未答也不会自动代选。`check --strict`把结构提醒视为未通过，不证明专业判断正确或用户已经认可。

全量模式保留`1_简报.md`、`2_作战图.md`、`3_日志.md`、`4_验收复盘.md`。旧版四文件和v0.2档案继续兼容。轻量档案不会被自动改写成全量；确需转换组织形式时，新建全量档案并引用原任务即可。

## 方法与工具

| 路径 | 用途 |
|---|---|
| [Skill入口](skill/expert-process/SKILL.md) | 选择用法和按缺口读取方法 |
| [共同核心](skill/expert-process/references/core.md) | 行业适配、人机分工、裁剪与知识范围 |
| [轻量用法](skill/expert-process/references/lite.md) | 默认直接解决问题，可选单文件续接 |
| [全量工作流](skill/expert-process/references/workflow.md) | 复杂任务的阶段、责任、记录与交接 |
| `cli/` | 记录、检查、查库和导出命令与测试 |
| `templates/` | 轻量、全量和卡片模板 |
| `tools/` | 按领域选用的确定性脚本，如颜色指标计算 |

`python3 cli/eca.py pack`生成Skill ZIP和单文件版，只包含通用方法和许可，不包含任务数据、卡片库、CLI、模板或工具脚本。独立Skill使用方法即可，需要CLI自动化时保留完整仓库。手机端专用版本及MCP接入尚未实现，不是本机使用的前提。

## 本地检查

```bash
python3 cli/tests/test_eca.py
python3 cli/eca.py check --strict
python3 cli/eca.py pack
```

测试使用隔离数据，不操作真实用户任务。结构检查、宿主选路和专业效果分别判断；生成资料不会自动上传，公开提交前仍需检查新增文件。

## 许可与致谢

本项目采用[Apache License 2.0](LICENSE)。感谢[DisCo / AREX-Skill](https://github.com/VectorSpaceLab/AREX-Skill)、[Skill Seekers](https://github.com/yusufkaraaslan/Skill_Seekers)和[OpenAI skill-creator](https://github.com/openai/skills/tree/49f948faa9258a0c61caceaf225e179651397431/skills/.system/skill-creator)提供的方法与结构参考。

各项目具体贡献、固定版本及改写范围见[致谢](ACKNOWLEDGEMENTS.md)；相关上游归属和许可见[NOTICE](NOTICE)。本项目不代表上述项目，也不依赖其运行时。

## 上游版本

[来源清单](upstream/SOURCES.json)列出研究时核对的352个文件及固定版本。公开仓库只提供来源元数据，不附带上游源码；运行本工具无需先下载这些上游项目。该清单不表示本项目复制或运行了全部列出文件。
