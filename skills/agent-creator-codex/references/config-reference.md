# Codex 角色配置参考

本文依据 2026-11-13 对 OpenAI `rust-v0.167.2` 源码的核对。
这是源码和文档依据，不是运行该版本二进制的记录；用户内部 CLI 的兼容性尚需在目标环境验证。

目录：[文件形式](#文件形式)、[常用字段](#常用字段)、[权限与禁用项](#权限与禁用项)、
[模型设置](#模型设置)、[父配置与静态检查边界](#父配置与静态检查边界)、[来源](#来源)。

## 文件形式

### 独立文件

项目角色放在 `.codex/agents/`，个人角色放在 `~/.codex/agents/`。
目标环境自定义 `CODEX_HOME` 时，以其实际目录为准；项目配置还受项目信任和管理策略影响。

每个文件定义一个角色，提供非空字符串 `name`、`description` 和 `developer_instructions`。
角色标识来自 `name`；文件名可以不同。正文放在 TOML 字符串内，不附加 Markdown 文件正文。

### 显式注册与配置层

先在 `.codex/config.toml` 中注册角色：

```toml
[agents.case-analyst]
description = "根据源码和日志调查搜索问题。"
config_file = "role-configs/case-analyst.toml"
```

这里引用 `.codex/role-configs/case-analyst.toml`。
`config_file` 相对声明它的配置文件所在目录解析，不相对终端工作目录解析。
引用的配置层可以仅提供需要覆盖的设置；元数据可由注册信息提供，`developer_instructions` 也可以省略。
本技能生成和检查配置层时，仍要求已填写的字段具有正确类型和有效内容。
在核对基准中，配置层里的非空 `name`、已填写的 `description` 和昵称列表可覆盖声明值；
通常省略重复元数据更容易维护。只有结合父声明，才能确认最终角色身份与合并结果。

配置层使用 `--kind role-layer` 检查。这个模式不读取父 `config.toml`，不判断引用是否存在、
角色是否重复注册或目标 Codex 是否支持该加载方式，也不从层内 `name` 推断注册身份或跨层查重。
不要把裸配置层放入独立角色扫描目录后，
仍然假设它只会按配置层加载。

## 常用字段

| 字段 | 类型与取值 | 说明 |
| --- | --- | --- |
| `name` | 字符串 | 独立文件必需且非空；配置层通常省略，由注册信息提供身份 |
| `description` | 非空字符串 | 说明何时委派给此角色；独立文件必需 |
| `developer_instructions` | 非空字符串 | 作为 developer 指令传递的角色行为要求；独立文件必需 |
| `model` | 字符串；本校验器不接受空白值 | 用户指定时保留；省略时使用运行时解析的默认设置 |
| `model_reasoning_effort` | 非空字符串 | 接受值取决于目标模型及客户端，不使用固定模型名单校验 |
| `model_reasoning_summary` | `auto`、`concise`、`detailed`、`none` | 摘要控制；模型是否实际支持仍需核验 |
| `model_verbosity` | `low`、`medium`、`high` | 输出详细程度；不等于输出长度保证 |
| `personality` | `none`、`friendly`、`pragmatic` | 基准 Schema 保留这些值，但后两项已不再选择风格；新角色一般省略 |
| `nickname_candidates` | 非空字符串数组 | 展示昵称；不是调用角色的标识 |
| `features` | TOML 表 | 仅部分关闭项能作为角色覆盖应用 |
| `skills` | TOML 表 | 仅下述关闭项能作为角色覆盖应用 |

`nickname_candidates` 在核对基准中会去除首尾空白，并拒绝空白项和重复项；
每项仅接受 ASCII 字母、数字、空格、连字符和下划线。这是昵称限制，不要套用到角色 `name`。

顶层字段必须放在各个 `[表]` 之前。例如写在 `[skills]` 后的 `developer_instructions`，
会成为 `skills.developer_instructions`，不会自动回到顶层。

## 权限与禁用项

角色文件不会替代父会话的沙箱、审批策略、模型提供方或 MCP 配置。
`sandbox_mode`、`approval_policy`、`model_provider`、`mcp_servers` 等会话设置，
不能被当作角色级权限开关。字段能够通过 TOML 解析，也不代表角色应用阶段会使用它。

“只读分析”可以写进指令，但它不是独立只读沙箱。
禁用 shell 工具仅影响 shell 工具；通过继承的 MCP、插件或其他工具访问资源的能力仍需分别确认。
MCP 服务器和工具限制应由父会话的实际配置管理，角色文件里的同名表不能作为可靠禁用手段。

### 功能关闭

在核对基准中，角色仅应用这些功能键的 `false` 值：

| 键 | 作用 |
| --- | --- |
| `features.shell_tool` | 关闭 shell 工具 |
| `features.apps` | 关闭对应应用功能 |
| `features.plugins` | 关闭对应插件功能 |
| `features.memories` | 关闭对应记忆功能；`memory_tool` 为兼容名称 |
| `features.request_permissions_tool` | 关闭对应权限请求工具 |

这些键应为布尔值。把它们设为 `true` 不能由角色启用父会话未提供的功能。
其他功能键不能仅凭出现在全局配置里，就推断它会在角色覆盖中生效。

### 技能关闭

- `[[skills.config]]`：每项含布尔值 `enabled`，并用 `name` 或 `path` 之一匹配技能；
  不要同时指定两个选择器，也不要省略选择器。
- `[skills.bundled]`：`enabled = false` 关闭继承的内置技能集合。
- `[skills]`：`include_instructions = false` 省略自动技能说明块。

角色只保留这些设置中的关闭项，不能使用 `enabled = true` 为自己增加技能。
`skills.max_context_tokens` 描述的是技能目录预算，角色应用时不会保留它；
它也不是整个 Agent 上下文的 token 上限。

## 模型设置

新角色默认省略模型和推理强度，由目标运行时沿用默认设置。
角色文件显式设置 `model` 或 `model_reasoning_effort` 时，核对基准会把它应用到已解析的子会话设置上；
只改模型可能仍保留此前解析的推理强度，因此需要确认二者兼容。

父配置中的 `agents.default_subagent_model`、`agents.default_subagent_reasoning_effort`，
委派请求的显式设置以及父会话默认值都会影响未被角色覆盖的字段。
不要为了演示而为用户写入某个固定模型，更不能将内部模型 ID 改成公开模型。
校验器只检查已覆盖字段的结构，不访问模型目录，也不发起模型调用。

## 父配置与静态检查边界

全局多 Agent 参数写在父配置的 `[agents]` 中，例如：

```toml
[agents]
enabled = true
max_concurrent_threads_per_session = 4
```

在当前公开文档中，并发数不包含主线程，`max_threads` 是旧别名。
这些键与 `[agents.<角色名>]` 都不是本脚本的检查目标；不要把父 `config.toml` 作为独立 Agent 文件校验。

校验器检查 TOML、独立角色必需项、已覆盖字段的类型与部分结构、重复角色名，
并对已知无效覆盖和尚未覆盖字段给出诊断。它不是完整 Schema 的副本。
未知字段显示 `WARNING`，表示需要核对目标版本；`--strict` 会因此返回非零退出码。
文件名差异和短中文提示不作为失败条件。

`[capabilities]`、`[constraints]`、`max_tool_calls`、`max_rounds`、
`stop_on_no_new_evidence` 没有本基准的原生角色字段依据，不主动生成。
需要内部扩展时先检查实际读取这些字段的实现；需要硬预算时由执行器计数、判断和停止。

## 来源

- [官方 Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [官方配置参考](https://learn.chatgpt.com/docs/config-file/config-reference)
- [`rust-v0.167.2` 角色文件解析](https://github.com/openai/codex/blob/rust-v0.167.2/codex-rs/agent-roles/src/agent_role_config.rs)
- [`rust-v0.167.2` 声明与文件合并](https://github.com/openai/codex/blob/rust-v0.167.2/codex-rs/agent-roles/src/loader.rs)
- [`rust-v0.167.2` 角色覆盖应用](https://github.com/openai/codex/blob/rust-v0.167.2/codex-rs/core/src/agent/role.rs)
- [`rust-v0.167.2` 技能配置](https://github.com/openai/codex/blob/rust-v0.167.2/codex-rs/config/src/skills_config.rs)
- [`rust-v0.167.2` 配置 Schema](https://github.com/openai/codex/blob/rust-v0.167.2/codex-rs/core/config.schema.json)

核对日期：2026-11-13。源码核对不等于已运行目标客户端；内部版本可能存在额外限制或扩展。
