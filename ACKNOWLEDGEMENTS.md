# 致谢与来源

Expert Process的工作流、卡片结构和检查工具参考了以下项目。感谢作者和贡献者公开这些方法与实现。本项目对所采用部分进行了重新表述、裁剪和本地实现，不包含上游整套运行时，也不代表上游项目。

| 项目 | 固定研究版本 | 参考与改写范围 | 上游许可 |
|---|---|---|---|
| [DisCo / AREX-Skill](https://github.com/VectorSpaceLab/AREX-Skill) | `ac3fe1afa80fb9a09775ecfb2b6cc3ba850a2db6` | Scope / Ground / Construct / Verify、来源证据、复用与刷新思路，重新组织到research、review、retro、forge等指南 | 仓库通用文档Apache-2.0；实际参考的DisCo CLI Creator指南按CLI的MIT许可 |
| [Skill Seekers](https://github.com/yusufkaraaslan/Skill_Seekers) | `5b5d8dfca263fa76e6daae9f292890b311ef36aa` | 异构来源、多源冲突与分阶段合并；`integrate.md`冲突处理参考并改写自`complex-merge.yaml`七阶段结构 | MIT |
| [OpenAI skill-creator](https://github.com/openai/skills/tree/49f948faa9258a0c61caceaf225e179651397431/skills/.system/skill-creator) | `49f948faa9258a0c61caceaf225e179651397431` | 触发边界、模型自由度、渐进披露、标准技能结构与结构检查规则；指南经重新表述，CLI检查以Python标准库重实现 | 该历史Skill的独立LICENSE.txt为Apache-2.0 |

上游归属和相关MIT许可全文保存在[NOTICE](NOTICE)，本项目许可见[LICENSE](LICENSE)。固定版本的原路径与哈希见[来源元数据](https://github.com/Ming-Sir-69/expert-process/blob/main/upstream/SOURCES.json)，该清单不表示复制了全部列出文件。

## 其他方法与算法来源

- 关卡的保存、等待和恢复思路参考[Claude Code用户输入](https://code.claude.com/docs/en/agent-sdk/user-input)、[LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)及[Codex App Server](https://learn.chatgpt.com/docs/app-server)。这里只借鉴状态交接方式，不引入这些项目的运行时。
- `tools/colormetrics.py`的对比度公式参考[WCAG contrast ratio](https://www.w3.org/TR/WCAG22/#dfn-contrast-ratio)，OKLab转换参考[Björn Ottosson的作者说明](https://bottosson.github.io/posts/oklab/)。作者提供public domain或MIT选项；本项目使用其public domain选项。
- 红绿色觉缺陷模拟的矩阵来自Gustavo M. Machado、Manuel M. Oliveira、Leandro A. F. Fernandes的2009年论文“A Physiologically-based Model for Simulation of Color Vision Deficiency”，数值对应[作者页面Table 1](https://www.inf.ufrgs.br/~oliveira/pubs_files/CVD_Simulation/CVD_Simulation.html)的severity 1.0。这里只使用表格中的科学数值并自行实现运算，不复制作者的外部程序，也不把数值表虚标为MIT授权代码。模拟结果用于辅助检查，不代替真实用户评估。

所有外部项目和作者名称仅用于来源归属，不表示其对本项目的认可或背书。
