# Codex 角色示例

以下均为配置示例，不是已在用户内部 CLI 执行的记录。
默认省略 `model` 和 `model_reasoning_effort`；用户明确指定时再按其环境填写。
命令中的占位路径需替换为真实路径。

目录：[独立分析角色](#独立分析角色)、[实现角色](#实现角色)、[依赖 MCP](#依赖-mcp)、
[关闭功能或技能](#关闭功能或技能)、[显式注册配置层](#显式注册配置层)、[委派与核验](#委派与核验)。

## 独立分析角色

文件：`.codex/agents/case-analyst.toml`。

```toml
name = "case-analyst"
description = "根据搜索 case、源码和日志调查异常，返回有依据的事实与候选原因。"
developer_instructions = """
你负责调查主 Agent 指定的搜索问题。
先确认实际结果、预期结果和输入条件，再检查相关代码和日志。
区分事实、假设和未知项；每项关键结论引用文件位置或运行证据。
只执行分析，不修改业务代码。
证据不足或继续调查需要扩大任务范围时，返回证据缺口和后续建议。
输出：问题概述、已确认事实、候选原因、验证结果、未解决事项。
"""
```

“不修改业务代码”是指令约束。需要强制只读时，另行确认父会话及继承工具的实际权限。

```bash
python "<技能目录>/scripts/validate-agent.py" "<项目目录>/.codex/agents/case-analyst.toml" --strict
```

## 实现角色

文件：`.codex/agents/implementer.toml`。父会话需具备任务所需的写入权限。

```toml
name = "implementer"
description = "按明确的验收条件完成一个范围受限的代码修改。"
developer_instructions = """
只实现委派消息指定的改动。
先读取相关代码和已有测试，再进行必要修改。
不调整无关依赖、架构或其他文件。
执行与改动风险匹配的验证；报告实际命令和结果，不把未运行的检查写成通过。
返回修改原因、涉及文件、验证结果和剩余问题。
"""
```

## 依赖 MCP

先在父会话配置中声明真实可用的 MCP 服务器，再在角色说明中描述依赖。
下面的服务器 ID 是示例；内部环境应替换为已有的配置，不自动新增外部连接。

父配置示例：

```toml
[mcp_servers.openaiDeveloperDocs]
url = "https://developers.openai.com/mcp"
```

独立角色 `.codex/agents/docs-researcher.toml`：

```toml
name = "docs-researcher"
description = "通过父会话已配置的官方文档 MCP 核对接口和配置项。"
developer_instructions = """
使用父会话提供的 openaiDeveloperDocs 工具核对文档。
给出来源链接，并区分文档明确说明与尚无依据的结论。
工具不可用时报告依赖缺失，不编造接口或引用。
"""
```

角色中的提示词不会创建 MCP 服务器；将 `mcp_servers` 写进角色文件也不代表已配置或禁用了服务器。

## 关闭功能或技能

文件：`.codex/agents/text-analyst.toml`。

```toml
name = "text-analyst"
description = "分析委派消息中的材料，返回可核对的结论。"
developer_instructions = "分析提供的材料，区分事实与推断，按条列出结论与依据。"

[features]
shell_tool = false

[skills]
include_instructions = false

[skills.bundled]
enabled = false

[[skills.config]]
name = "example-skill"
enabled = false
```

`example-skill` 是演示名称，实际使用时替换为需要关闭的真实技能。
可改用 `path` 匹配具体技能，但不要在同一条配置中同时填写 `name` 和 `path`。
上述配置不构成 MCP 工具禁用清单，也不能证明所有外部资源访问都已被阻止。

## 显式注册配置层

`.codex/config.toml`：

```toml
[agents.reviewer]
description = "审查指定差异的正确性及回归风险。"
config_file = "role-configs/reviewer.toml"
```

被引用的 `.codex/role-configs/reviewer.toml`：

```toml
developer_instructions = "只审查指定差异，返回问题位置、触发条件和证据；不修改文件。"
```

该文件通过注册信息获得角色身份，不需要重复独立文件的三个必填项。
配置层也可以不覆盖 `developer_instructions`，仅提供有实际需要的其他受支持设置。

```bash
python "<技能目录>/scripts/validate-agent.py" "<项目目录>/.codex/role-configs/reviewer.toml" --kind role-layer --strict
```

这个命令不检查父 `config.toml`，也不检查上面的相对路径是否正确；需单独确认引用能解析到该文件。

## 委派与核验

在目标 Codex 中明确要求使用角色，例如：

```text
请使用 case-analyst 子 Agent 分析以下 case。
输入文件：<真实 case 路径>
相关源码：<真实源码路径>
实际结果与预期结果：<具体说明>
不要修改业务代码。等待子 Agent 完成后，汇总证据、候选原因和待验证事项。
```

子 Agent 是否继承父会话历史由目标运行时及委派参数决定，因此仍需传递必要输入。
静态检查后，在目标客户端观察是否按指定角色创建线程、实际采用的设置和任务返回结果。
没有执行委派时，只能报告静态检查结果，不能报告“角色已运行验证”。
