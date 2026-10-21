---
name: expert-process
license: Apache-2.0
description: 按当前问题的知识缺口和协作需要，选用行业方法、专业视角、人机提问与必要检查。默认轻量处理小问题，长期、多阶段或需要交接时使用全量工作流；用于设计、开发、文档、分析与规划，或用户要求按专业方法处理时。不为简单问答、闲聊额外启动流程。
---

# Expert Process

先读[共同核心](references/core.md)。**默认采用最小充分的方法；轻量与全量共用同一核心，不维护两套判断标准。** Agent承担专业取舍，用户提供其专属信息和必要授权。

## 选择入口

| 当前需要 | 读取 |
|---|---|
| 局部问题、边界明确，或只需补一种能力 | [轻量用法](references/lite.md)：可直接处理，不建档 |
| 多阶段、依赖复杂，或一份记录已难以支撑持续协作交接 | [全量工作流](references/workflow.md)：组织必要阶段与活文档 |

按实际需要增减方法，不把规模、来源数量或一次高风险操作当成整套升级的自动开关。专业判断、记录形式和执行工具分别选择；达到当前完成条件就交付。

## 按缺口取用

- 缺行业知识、标准或依据：[调研](references/research.md)。不必先研究整个行业。
- 有相互依赖的阶段、角色或重要分歧：[整合](references/integrate.md)。七字段是边界检查角度，小问题无需填表。
- 缺本人专属信息或尚未获得的动作授权：[关卡](references/gates.md)。已有答案与授权不重复问；不用等待代替答复。
- 需要检查交付与未知项：[验收](references/review.md)。按实际产物和风险检查，不以文件齐全代替结果质量。
- 确有复用价值：[卡片与范围](references/cards.md)、[复盘](references/retro.md)。当前任务的选择不自动变成全局规则。
- 重复需求已有稳定经验：[固化技能](references/forge.md)。一次性任务直接完成。

## 本机使用

完整工具包提供CLI；独立Skill包只包含方法与许可，不包含CLI、模板或工具脚本。在工具包根目录执行：

```bash
python3 cli/eca.py guide lite                 # 默认入口；只读展示方法，不建档
python3 cli/eca.py guide full                 # 需要时读取全量用法
python3 cli/eca.py new example --mode lite     # 可选：单文件续接记录
python3 cli/eca.py new example --mode full     # 多阶段任务：四份活文档
```

任务、卡片和导出写入外部数据目录，由`--data-dir`、`ECA_DATA_DIR`、用户配置或平台默认位置确定。工具源码目录只存可维护的工具文件，不写本次任务记录或私人资料。无命令能力时使用方法即可，不假装执行CLI，也不强制创建替代档案。
