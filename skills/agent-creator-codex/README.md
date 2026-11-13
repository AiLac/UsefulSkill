# agent-creator-codex

用于创建、修改和排查 Codex 自定义 subagent 的技能。
它提供角色编写步骤、字段参考、完整示例，以及一个 Python 标准库校验脚本。

例如，生成的配置把 `name` 写成 `[name = "case-analyst"]` 时，脚本会报告 TOML 语法错误；
已知字段类型错误会被报告，未覆盖字段会提示核对目标版本。
检查通过表示文件通过本脚本的静态检查，不表示目标 Codex 已加载角色或模型已经运行成功。

## 使用

将整个技能目录放入目标 Codex 实际加载的技能目录，保留 `scripts/` 和 `references/`。
这一步仅是部署说明；本仓库没有自动安装、联网下载或修改全局权限的逻辑。
内部版本的技能目录和加载方式，以该版本的规范为准。

技能可用后，可以明确调用：

```text
$agent-creator-codex 为当前项目创建一个搜索 badcase 分析角色。
默认继承模型设置，返回已确认事实、候选原因和证据缺口。
完成后执行静态检查，并明确哪些加载行为还没有验证。
```

## 两种角色文件

| 类型 | 说明 | 模式 |
| --- | --- | --- |
| 独立角色 | `.codex/agents/*.toml` 或个人角色目录下的文件；含 `name`、`description`、`developer_instructions` | 默认 `standalone` |
| 注册配置层 | 由父 `config.toml` 的 `[agents.<名称>].config_file` 引用；可省略元数据和角色指令 | `--kind role-layer` |

校验配置层不会同时检查父配置、相对引用路径或父级注册名称。纯配置层宜放在 `role-configs/` 等单独目录，
避免又被按独立角色发现。

## 静态检查

需要 Python 3.11+，仅使用标准库。将占位路径替换为真实路径：

```bash
python "<技能目录>/scripts/validate-agent.py" "<独立角色文件或目录>" --strict
python "<技能目录>/scripts/validate-agent.py" "<配置层文件>" --kind role-layer --strict
```

脚本检查 TOML、独立角色必需项、已覆盖字段的类型和结构，以及重复角色名。
对会被忽略的覆盖和尚未覆盖字段给出警告。`--strict` 让错误或警告返回非零退出码；
不带该参数时，只有警告可能仍返回零退出码。
文件名与 `name` 不同或中文指令较短，不会因此被判为无效。

## 能力范围

- 校验器不是完整 Codex Schema，不确定的字段仍需核对目标版本。
- 默认不指定模型或推理强度；用户提供的内部模型 ID 会保留，但其可用性需在内部环境确认。
- `developer_instructions` 是开发者指令，不是 system 消息或权限配置。
- 角色继承父会话权限与 MCP 配置；提示词中的“只读”“最多几轮”不是执行器硬限制。
- 子 Agent 获得的上下文由实际委派方式决定，不假设总能或绝不能看到父会话历史。
- 静态检查、目标客户端加载和实际委派分别报告；未执行的检查不会标为通过。

## 内容与来源

- [SKILL.md](SKILL.md)：执行步骤与按需读取入口。
- [配置参考](references/config-reference.md)：字段、注册方式和权限边界。
- [完整示例](references/agent-examples.md)：分析、实现、MCP 依赖和配置层示例。
- [故障排查](references/troubleshooting.md)：按可观察现象定位问题。
- [校验脚本](scripts/validate-agent.py)：文件或目录的静态检查。

本版于 2026-11-13 核对 OpenAI `rust-v0.167.2` 源码；这不代表运行过该版本二进制，
也不代表已经验证用户内部 CLI。具体官方源码链接见配置参考。
公开文档入口：[Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)、
[配置参考](https://learn.chatgpt.com/docs/config-file/config-reference)。
