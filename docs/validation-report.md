# agent-creator-codex 验证记录

日期：2026-11-13。以下为实际执行结果；目标用户内部 Codex 的加载、模型调用和权限行为未执行。

## 环境与依据

| 项目 | 实际情况 |
| --- | --- |
| 本地测试 | Linux，Python 3.12.14，标准库 `unittest`、`tomllib` |
| 可用客户端 | `codex-cli 0.167.0-alpha.4`；执行了版本及帮助检查 |
| 规则对照 | OpenAI `rust-v0.167.2` 源码及 2026-11-13 官方文档；未运行该 tag 的二进制 |
| 上游基线 | CowboyLogic/ai-dev 提交 `7376c94c1a991acf965eeb7c01c2a15dc4c5e7e1` |
| 模型与凭据 | 校验脚本不读取凭据、不请求模型、不联网 |

## 1. 自动回归

从仓库根目录运行：

```bash
python -m unittest discover -s tests -v
```

实际结果：**23 个测试全部通过，退出码 0**。测试中还包含多组参数化子用例；这里没有把子用例数量当作缺陷数量。
完整命令、环境与输出见 [unittest-results.json](evidence/unittest-results.json)。

覆盖内容包括：必需字段、模型与推理强度字符串、明确枚举、features/skills 结构、昵称限制、未知字段与严格模式、两种配置形式、短中文和不同文件名、真实角色重名、重叠路径与符号链接、空目录、丢失文件、错误编码、错误容器，以及深层 TOML 嵌套。

深层嵌套是独立代码审查补充发现的问题：原先未捕获 `RecursionError`。已在解析区域处理该异常；新增用例检查它返回错误并继续处理后续合法文件。

## 2. 对原输入的前后对照

[validator-comparison.json](evidence/validator-comparison.json) 保留 **11 组同输入的前后结果**、原始命令和输入文件内容。记录中的绝对路径是执行当时的临时路径，不是安装路径要求；无效编码输入以十六进制保存。

| 输入 | 原版实际结果 | 优化版实际结果 |
| --- | --- | --- |
| 合法最小角色 | 严格模式退出 0 | 退出 0，无错误或警告 |
| `model = 123` | 严格模式退出 0 | 退出 1，指出模型应为字符串 |
| 无效 verbosity | 严格模式退出 0 | 退出 1，指出有效枚举 |
| features 为字符串 | 严格模式退出 0 | 退出 1，指出应为表 |
| skills 为布尔值 | 严格模式退出 0 | 退出 1，指出应为表 |
| skills 布尔字段为字符串 | 严格模式退出 0 | 退出 1，指出应为布尔值 |
| 未覆盖字段，严格模式 | 退出 1，警告 | 退出 1，明确未覆盖及版本核对要求 |
| `sandbox_mode = []` | `TypeError` traceback | 退出 1，明确类型错误，无 traceback |
| 未覆盖字段，普通模式 | 退出 0，警告 | 退出 0，警告；不是对字段生效的认可 |
| 同时传目录及同一文件 | 与自身重名，退出 1 | 只检查 1 个文件，退出 0 |
| 非 UTF-8 文件后跟合法文件 | `UnicodeDecodeError`，批次中断 | 退出 1，输出编码诊断，完成 2 个文件的检查 |

这些结果证明已复现输入的行为变化，不是性能基准，也不证明所有可能输入都被完整校验。

## 3. 文档、示例与独立使用

- 文档中的 **10 个 TOML 代码块**全部完成语法解析。
- 其中 **5 个独立角色和 1 个配置层**按对应模式通过 `--strict`，均为 0 errors / 0 warnings。
- 其余 **4 个父配置块**仅做语法解析，没有把父 `config.toml` 当作独立角色校验。
- 随技能提供的 `assets/case-analyst.toml` 通过严格校验。
- 另一个未接收预期答案的 agent 从 `SKILL.md` 开始，按真实需求生成 Java 搜索问题分析角色，保留指定内部模型 ID，完成严格检查，并复现原错误配置的诊断。记录及完整生成内容见 [forward-test-results.json](evidence/forward-test-results.json)。

独立使用没有调用内部模型或运行真实 case。生成文件中的“只读”“三轮”和“无新证据停止”被准确标为行为指令，未宣称为执行器强制限制。

可在仓库根目录复查随包示例：

```bash
python skills/agent-creator-codex/scripts/validate-agent.py skills/agent-creator-codex/assets/case-analyst.toml --strict
```

## 4. 文档简化

主 `SKILL.md` 从 **355 行减少到 121 行**；固定流程保留在主文件，字段、例子、排错细节按需读取。新版本保留单个标准库校验脚本，没有加入 Schema 框架、第三方 Python 依赖、云服务或自动下载逻辑。

行数变化只说明主文件更短，不等同于推理成本或生成质量的量化提升。实际使用证据见上一节。

## 5. GitHub 与剩余验证

代码已提交至 `AiLac/UsefulSkill` 的 `main`：
[2026c49e0c6f8026fc6092b2cc7bca9f345f8096](https://github.com/AiLac/UsefulSkill/commit/2026c49e0c6f8026fc6092b2cc7bca9f345f8096)。
读取远端 Git tree 后，20 个交付文件的 blob SHA 全部与本地内容一致；另回读了 `SKILL.md` 内容。

[GitHub Actions 运行 43356734862](https://github.com/AiLac/UsefulSkill/actions/runs/43356734862) 已完成，结论为 **success**：

| 远端环境 | 实际 Python 版本 | 结果 |
| --- | --- | --- |
| ubuntu-latest | 3.11.18 | 23 个测试通过，随包示例严格检查通过 |
| windows-latest | 3.12.10 | 23 个测试通过，随包示例严格检查通过 |

两个任务的符号链接测试均实际通过，没有跳过。运行 ID、对应代码提交、步骤结果与关键日志摘录见
[github-actions-results.json](evidence/github-actions-results.json)。后续补充的这份远端验证记录不修改技能或测试代码。

以下项目仍需在用户的实际目标环境验证：

1. 内部 Codex 是否按预期发现和加载角色，以及其扩展 Schema 是否不同于官方基准。
2. `maas-glm-5.2-volcengine-codeagent` 是否可用、provider 绑定和继承的推理强度是否兼容。
3. 实际创建该角色后采用的模型、上下文和工具设置。
4. 真实案例的分析质量及停止行为；若要求硬性只读或调用配额，需要执行器或父会话权限控制。

`codex doctor --help` 已检查，但没有执行完整 doctor。它涉及认证、网络及其他诊断，整体退出码不能直接代表角色加载成功；静态检查也不替代这些运行时验证。
