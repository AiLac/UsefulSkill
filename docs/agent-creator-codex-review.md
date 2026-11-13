# agent-creator-codex 审查与优化依据

审查日期：2026-11-13。

## 结论与来源

建议保留上游技能的基本结构，修正已确认的校验缺陷和文档偏差。它已经正确说明 Codex 使用 TOML 定义角色、子 agent 继承父会话权限及 MCP 配置；主要问题是部分非法输入可以通过严格检查、异常输入会中断批量检查，以及文档对上下文继承的描述过于绝对。这些结论来自实际运行输出和源码对照，不能据此推断生成这些材料的模型能力。

本次任务开始时，[AiLac/UsefulSkill](https://github.com/AiLac/UsefulSkill) 为空。本次导入和优化的基线是 [CowboyLogic/ai-dev 的 agent-creator-codex](https://github.com/CowboyLogic/ai-dev/tree/7376c94c1a991acf965eeb7c01c2a15dc4c5e7e1/skills/agent-creator-codex)，固定提交为 `7376c94c1a991acf965eeb7c01c2a15dc4c5e7e1`，不是对上游仓库直接修改。导入时应保留上游来源和 MIT 许可证信息。

审查使用三类证据，分别说明它们能够证明什么：

- **原脚本的实际输出**：[validator-comparison.json](evidence/validator-comparison.json) 保留了 11 组原始调用，以及相同输入在优化版上的结果，包括输入、命令、退出码、标准输出和错误输出。这些记录证明校验器在给定输入下的行为。
- **官方文档及固定版本源码**：以 OpenAI Codex `rust-v0.167.2` 为对照，确认字段类型、角色加载方式和继承规则。源码审查不等于运行过该版本。
- **本地命令检查**：实际执行 `codex --version` 得到 `codex-cli 0.167.0-alpha.4`，并执行了 `codex doctor --help`。没有运行完整 doctor、调用模型或创建测试 subagent，因此没有证明本地运行时已接受优化后的配置。

## 问题证据、收益与修改范围

下表中的“实际复现”来自修复前记录；“源码确认”表示已读取对应实现，但不冒充已执行用例。原脚本定位见 [validate-agent.py](https://github.com/CowboyLogic/ai-dev/blob/7376c94c1a991acf965eeb7c01c2a15dc4c5e7e1/skills/agent-creator-codex/scripts/validate-agent.py)。

| 问题与证据 | 预期收益 | 改动范围 | 验证方式 |
| --- | --- | --- | --- |
| **类型及枚举漏检，实际复现。** `model = 123`、`model_verbosity = "impossible"`、`features = "disabled"`、`skills = false`、`skills.include_instructions = "false"` 五组输入均在 `--strict` 下返回 0，且没有错误或告警。 | 在交给 Codex 前发现明显错误，避免把“脚本通过”误解为配置有效。 | 补充已支持字段的类型检查，以及 summary、verbosity 等明确枚举；检查 features、skills 的结构。 | 对每个原有漏检输入要求非零退出，并配套合法值用例，避免修复后误拒绝有效配置。 |
| **异常输入使程序崩溃，实际复现。** `sandbox_mode = []` 触发 `TypeError`；非法 UTF-8 文件触发 `UnicodeDecodeError`，其后的合法文件没有得到检查。 | 单个坏文件得到清楚的错误说明，其他文件仍可完成检查。 | 在使用集合、字符串或表操作前检查类型；处理读取和解码失败。 | 输入数组、表、无效编码及后续合法文件，要求无未捕获 traceback，并确认后续文件被处理。 |
| **同一文件被重复计数，实际复现。** 同时传入目录和其中的文件，原脚本报告该文件与自身重名，退出 1。 | 区分重复输入路径和两个文件定义同名角色。 | 扫描后按规范化路径去重；角色名称按去除首尾空白后的值比较。 | 目录与文件重叠输入只检查一次；两个不同文件使用同名或首尾空白等价的名称仍应报告冲突。 |
| **独立文件与引用层混用，源码确认。** 原脚本统一要求三个字段，但上游参考文档和官方解析器允许 `config_file` 引用层省略部分元数据。 | 合法的角色配置层不再因采用另一种加载方式被误报。 | 增加 `--kind standalone\|role-layer`，默认继续检查独立角色；不扩展为完整 `config.toml` 解析器。 | 独立文件缺必需字段应失败；引用层可省略对应字段，但提供空白 description 或 developer_instructions 仍应失败。 |
| **nickname 边界漏检，源码确认。** 原脚本仅检查字符串数组；官方还检查非空数组、去除首尾空白后的空值和重复，以及允许的字符。 | 防止原脚本接受官方加载器会拒绝的昵称列表。 | 补充 nickname 候选值检查；不把同样的字符规则套到角色 name。 | 检查空数组、空白、重复、非 ASCII 候选，以及合法空格、连字符和下划线。 |
| **风格建议影响正确性判断，源码确认。** 指令少于 40 个字符、文件名与 name 不一致都会产生告警，进而被 `--strict` 拒绝。官方没有这些硬性要求。 | 有效的简短中文指令和不同文件名可以通过正确性检查。 | 去掉这两项对通过结果的影响；指令质量建议留在写作指导中。 | 使用短中文指令和文件名不同但元数据合法的文件，确认通过。 |
| **未知字段的含义不够明确，实际复现及源码确认。** `[constraints]` 在默认模式仅告警并返回 0，严格模式返回 1；同时原白名单没有覆盖官方完整配置类型。 | 区分官方基准没有依据的字段、已知不生效字段，以及当前工具尚不能确认的字段。 | capabilities、constraints 给出明确告警和改写提示，`--strict` 阻断；其他未覆盖字段保留“需按目标版本核对”的告警，不否定未经检查的内部扩展。 | 分别检查外来字段、父会话专属字段和未知扩展字段；核对消息与退出码，不宣称本工具覆盖全部官方 schema。 |
| **文档存在确定偏差。** 上游称子 agent 不看父对话，但 V2 默认继承全部历史；参考文档还列出已移除的 `approval_policy = "untrusted"`，并将 developer 指令描述为 system 级。 | 让用户正确理解角色实际获得的信息和约束，避免照文档生成错误配置。 | 精简 SKILL.md，将细节放到相应参考文档；修正上下文、指令层级、版本和验证说明。 | 对照下列固定版本源码及官方文档审阅；示例与校验器使用同一组规则。 |

修复前 11 组调用还包括一个合法最小文件的通过记录，用于避免只展示失败样例。未知字段的默认模式与严格模式是两次独立调用，不能把它们描述为“两个不同缺陷”。

## 需要保持准确的行为边界

**上下文是否继承由创建方式决定。** 在本次核对的实现中，V1 使用 `fork_context`，默认不继承，设为 true 时继承；V2 使用 `fork_turns`，默认 `all`，设为 `none` 时不继承。创建角色的技能应提醒调用者查看目标运行时实际暴露的工具参数，并在任务消息中写清目标、输入和预期输出，不能写成“一定看不到父对话”。

**角色文件检查与角色加载检查是两件事。** 独立文件需要 `name`、`description`、`developer_instructions`。显式注册使用 `[agents.<name>]` 和 `config_file` 时，部分信息可以来自声明表。`--kind role-layer` 只检查被引用的文件；没有读取声明它的配置，就不能确认最终角色名称、合并后的 description、路径解析、项目可信状态或是否会被发现。

**行为指令不是权限隔离。** 在 developer_instructions 中要求“不编辑文件”“最多调查三轮”“没有新证据时停止”，表达的是 agent 应遵循的行为；它们不能自动建立只读沙箱或硬性调用预算。当前官方角色文件继承父会话的权限、审批、provider 和 MCP，不能通过写入 sandbox_mode、approval_policy 或 mcp_servers 覆盖父会话。需要硬限制时，应由实际执行器或父会话配置执行，并单独验证。

**配置裁剪也有明确范围。** 角色可关闭文档列明的功能和继承的 skills，但不能通过任意 `features.* = true` 扩大能力。关闭 `skills.include_instructions` 只是省略自动技能说明，不等于禁用所有技能。`skills.config` 的 name/path 选择器无效时，运行时可能告警并忽略；本工具可以为防止配置无效而报错，但应说明这是检查规则，不能伪称原生 TOML 解析失败。

**版本影响判断。** `agents.max_depth` 在核对的源码中仅适用于 V1，V2 忽略。`model_reasoning_effort` 是非空字符串，具体支持的值取决于模型及运行时，不应固定为少数枚举。内部 Codex 的扩展字段需要其版本源码、schema 或实际加载证据支持；当前官方参考只能作为对照，不能证明内部实现一致。

## 实施取舍与验收

本次保留 Python 3.11+ 标准库和单个校验脚本，围绕已证实问题补充检查、模式选择和异常处理，并精简文档。不会引入全量 schema 框架、云服务依赖或自动模型选择。未知字段保守告警，是为了承认静态检查的覆盖边界；它不是对字段已经生效的认可。

验证分为三个层次：

1. **静态回归**：复跑上述实际输入，增加角色层、昵称边界、短中文、重复路径及容错用例，记录预期与实际退出码、错误内容以及是否出现 traceback。
2. **目标版本加载检查**：由具备目标环境的一方运行加载诊断，检查与本角色有关的启动告警。完整 `codex doctor` 同时检查认证、网络等内容，总退出码不能直接代表角色文件结果。
3. **运行时检查**：在实际 Codex 会话中点名创建角色，观察模型、工具和任务结果。此步骤才能补充实际行为证据；仅看静态校验通过不能替代它。

**本报告记录审查依据和拟定修复范围，不预先宣称修复通过。** 实施后的命令、结果、覆盖范围及未执行项目统一填写到 [validation-report.md](validation-report.md)。若没有进行目标版本或模型调用测试，应在那里继续明确标为未执行。

## 官方对照资料

官方文档核对日期为 2026-11-13；源码使用固定 tag `rust-v0.167.2`，避免把未来主分支变化混入本次结论。

| 资料 | 本次核对内容 |
| --- | --- |
| [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents) | 独立文件、模型优先级、父权限及 MCP 继承、功能裁剪。 |
| [Configuration Reference](https://learn.chatgpt.com/docs/config-file/config-reference) | `[agents]` 与显式注册、当前审批策略、skills 字段。 |
| [CLI Reference](https://learn.chatgpt.com/docs/cli/reference) | doctor、debug models 的用途及限制。 |
| [agent_role_config.rs](https://github.com/openai/codex/blob/rust-v0.167.2/codex-rs/agent-roles/src/agent_role_config.rs) | 独立文件与 role_name_hint 的区别，名称规范化及 nickname 校验。 |
| [loader.rs](https://github.com/openai/codex/blob/rust-v0.167.2/codex-rs/agent-roles/src/loader.rs) | 角色发现、声明与文件的合并、重复角色及启动告警。 |
| [role.rs](https://github.com/openai/codex/blob/rust-v0.167.2/codex-rs/core/src/agent/role.rs) 与 [child_config.rs](https://github.com/openai/codex/blob/rust-v0.167.2/codex-rs/core/src/agent/child_config.rs) | 角色可应用字段、skills/features 裁剪、模型及运行时权限继承。 |
| [multi_agents_spec.rs](https://github.com/openai/codex/blob/rust-v0.167.2/codex-rs/core/src/tools/handlers/multi_agents_spec.rs) 与 [V2 spawn.rs](https://github.com/openai/codex/blob/rust-v0.167.2/codex-rs/core/src/tools/handlers/multi_agents_v2/spawn.rs) | V1/V2 的上下文继承参数与默认值。 |
| [config.schema.json](https://github.com/openai/codex/blob/rust-v0.167.2/codex-rs/core/config.schema.json) 与 [skills_config.rs](https://github.com/openai/codex/blob/rust-v0.167.2/codex-rs/config/src/skills_config.rs) | 字段类型、枚举、developer 消息层级、skills 选择器。schema 不包含全部兼容别名和角色加载语义。 |
| [doctor.rs](https://github.com/openai/codex/blob/rust-v0.167.2/codex-rs/cli/src/doctor.rs) | `config.load` 报告启动告警，但不检查活动线程覆盖值。 |
