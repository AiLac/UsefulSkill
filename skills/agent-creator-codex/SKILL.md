---
name: agent-creator-codex
description: 创建、修改或排查 Codex 自定义 subagent 的 TOML 文件和角色注册配置。用于选择角色字段、编写 developer_instructions、检查配置语法与已知字段、排查角色未加载或模型和权限行为不符。适用于独立 .codex/agents/*.toml 文件及 config_file 引用的配置层；不用于创建通用 Skill、修改全局权限或实现业务 Runner。
---

# Codex Subagent 创建与检查

生成目标 Codex 能识别的角色配置，并分别报告静态检查结果和实际加载结果。
先确认目标版本；不能因为字段名称看起来合理，就把它写成 Codex 原生配置。

来源基准：2026-11-13 核对 OpenAI `rust-v0.167.2` 源码。
该基准不代表运行过此版本 CLI，也不代表验证过用户的内部定制版。

## 1. 确认输入与目标环境

1. 明确角色职责、输入、允许修改的内容、返回格式及停止条件。
2. 读取已有项目说明、相关配置和同类角色文件，保留用户已有约定。
3. 能访问目标 CLI 时，记录 `codex --version`；内部版还需核对其配置规范或源码。
4. 只在任务需要时读取下方参考文件。不要自动安装客户端、下载模型或修改全局权限。

用户未指定模型或推理强度时，默认省略 `model` 和 `model_reasoning_effort`，让运行时解析默认值。
用户已提供内部模型 ID 时原样保留；本技能不以公开模型名单替换它，也不证明该模型可用。

## 2. 选择配置形式

| 形式 | 位置与必需信息 | 校验方式 |
| --- | --- | --- |
| 独立 Agent 文件 | 项目 `.codex/agents/*.toml` 或个人 `~/.codex/agents/*.toml`；含非空 `name`、`description`、`developer_instructions` | 默认 `standalone` |
| 显式注册的配置层 | 在 `config.toml` 的 `[agents.<名称>]` 中声明角色，并用 `config_file` 引用 TOML 层 | `--kind role-layer` |

独立文件与配置层不要混用必填规则。配置层可以省略角色元数据和 `developer_instructions`；已提供的字段仍须有效。
为避免纯配置层又被当作独立 Agent 扫描，优先把它放在 `.codex/role-configs/` 等单独目录。
`config_file` 的相对路径以声明它的 `config.toml` 所在目录解析。
校验配置层不等于检查了父配置、角色名称或引用路径；这些要另外核对。

## 3. 编写最小配置

以下是独立角色文件的示例，不包含默认模型覆盖：

```toml
name = "case-analyst"
description = "根据源码和日志分析搜索 badcase，分别报告事实、假设和证据缺口。"
developer_instructions = """
分析主 Agent 提供的 case、源码和日志。
区分已确认事实与待验证假设，每项结论引用具体证据。
只执行分析，不修改业务代码；证据不足时报告未知项。
返回问题概述、候选原因、验证结果和下一步建议。
"""
```

- 将顶层字段写在 `[features]`、`[skills]` 等表之前，避免意外改变字段归属。
- 写 `name = "case-analyst"`，不要写 `[name = "case-analyst"]`。
- `developer_instructions` 是开发者指令内容，不是 system 消息或权限配置。
- 文件名与 `name` 一致便于维护，但不把不一致或简短中文指令判为配置错误。
- 不生成无原生依据的 `[capabilities]`、`[constraints]`、`max_tool_calls` 等字段。
  若用户声称有内部扩展，先取得内部 Schema、读取源码或执行证据，再单独说明兼容范围。

把指令写成“职责、范围、处理方法、返回内容、停止条件”。
子 Agent 能收到多少父会话上下文由运行时的委派方式决定；任务消息仍应明确必要输入、路径和预期输出。

## 4. 分清行为要求与权限

角色继承父会话的沙箱、审批设置、模型提供方和 MCP 服务器配置。
在角色文件里添加 `sandbox_mode`、`approval_policy` 或 `mcp_servers`，不能据此承诺改变这些设置。
禁用 shell 工具也不等于禁用所有 MCP 工具；实际限制要在父会话及相应工具配置中确认。

“只读”“最多 3 轮”“没有新证据就停止”等提示词是行为要求。
需要保证调用次数、上下文预算或停止条件时，必须由实际执行器检查并执行；本技能不提供该执行器。
角色可应用的功能与技能禁用项见 [配置参考](references/config-reference.md)。

## 5. 执行静态检查

使用 Python 3.11+。将下面的占位路径替换为已确认的真实路径；有空格时保留引号。
脚本路径从技能目录取，目标路径从用户项目取，不假设两者共用工作目录。

```bash
python "<技能目录>/scripts/validate-agent.py" "<目标文件或目录>" --strict
```

对 `config_file` 引用的配置层使用：

```bash
python "<技能目录>/scripts/validate-agent.py" "<配置层文件>" --kind role-layer --strict
```

默认模式为 `--kind standalone`；目录检查递归处理 `.toml` 文件。
角色名查重仅用于独立文件；`role-layer` 不从层内 `name` 推断父配置注册的身份。

| 结果 | 处理方式 |
| --- | --- |
| `ERROR` | 修正可确定的语法、字段类型、必需项或结构错误，再检查 |
| `WARNING` | 核对被忽略字段、尚未覆盖字段或版本差异，不宣称已生效 |
| 严格模式非零退出 | 本次静态检查未通过；不得仅凭已生成文件报告完成 |
| 严格模式通过 | 仅说明未发现本脚本覆盖范围内的问题，继续核验目标客户端 |

未知字段属于“校验器尚未覆盖、需要目标版本确认”，不能一概断言运行时一定拒绝或一定忽略。
`--strict` 会让警告阻断通过；不带该选项时，只有警告可能仍返回零退出码。
本脚本不实现完整 Codex Schema，不验证模型账户权限，也不证明角色已被加载或调用。

## 6. 核验加载并交付

1. 对显式注册方式，单独检查角色表和 `config_file` 的实际解析路径。
2. 在可用的目标客户端重新加载配置，检查启动诊断；先确认帮助中存在诊断命令再使用。
3. 若目标版本提供 `codex doctor`，可检查其诊断；不把这个命令当作所有版本的共同接口。
4. 明确要求客户端按 `name` 委派一个范围很小的任务，观察角色线程、模型设置及返回结果。
5. 区分“文件已写入”“静态检查通过”“角色已加载”“实际任务已验证”。没有执行的项写明未验证。

交付时报告文件路径、目标版本、配置形式、实际执行的检查命令和结果，以及剩余的不确定性。
无法访问内部 CLI 时，完成能做的静态检查并列出内部核验步骤，不编造启动日志或委派记录。

## 按需读取

| 资源 | 何时读取 |
| --- | --- |
| [配置参考](references/config-reference.md) | 选择可选字段、禁用功能或核对注册方式 |
| [完整示例](references/agent-examples.md) | 需要独立角色、配置层、MCP 依赖或技能禁用示例 |
| [故障排查](references/troubleshooting.md) | 角色未加载、未使用或行为与预期不符 |
| [校验器](scripts/validate-agent.py) | 执行检查或核对当前覆盖范围 |

官方入口：[Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)、
[配置参考](https://learn.chatgpt.com/docs/config-file/config-reference)。
