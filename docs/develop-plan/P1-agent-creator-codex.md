# Agent Creator Codex Implementation Plan

**Goal:** 修复角色校验中的漏检、误报和崩溃，使技能准确生成并检查 Codex 自定义角色。

**Architecture:** 保留一个 Python 标准库校验脚本和按需读取的参考文档。区分独立角色文件与显式注册引用的配置层；静态检查不替代目标 Codex 加载及调用验证。

**Tech Stack:** Python 3.11+、tomllib、unittest、TOML、Markdown。

**Spec:** [审查判断与证据](../agent-creator-codex-review.md)。修改前的判断已在会话中给出。

## Global Constraints

- 来源：CowboyLogic/ai-dev，提交 `7376c94c1a991acf965eeb7c01c2a15dc4c5e7e1`。
- 对照：2026-11-13 官方文档及 `openai/codex` 的 `rust-v0.167.2` 源码。
- 保留 Python 3.11+ 标准库运行方式，不增加第三方依赖、运行服务或通用 Schema 引擎。
- 目标仓库初始为空；仅引入并优化本技能，保留原 MIT 授权和来源说明。
- 不安装个人技能，不修改用户的 Codex 全局配置、凭据、权限或 MCP 设置。
- 不硬编码可用模型清单或 reasoning effort 枚举。
- `--strict` 表示警告也失败，不表示完整官方 Schema 或真实运行验证。

## Review Focus

1. 非字符串模型设置、错误枚举和错误的 features/skills 容器不能被严格检查放过。
2. 非 UTF-8 文件、错误的 sandbox 容器不能导致 traceback 或跳过后续文件。
3. 重复输入路径和不同文件中的真实重名必须区别处理。
4. 合法的短中文指令、文件名不同于 name，不能仅因风格被阻止。
5. 注册配置层可以省略角色元数据，但不能把这种检查结果当作完整注册验证。

## Task 1: 可复现的回归场景

**Files:** `tests/test_agent_creator_codex.py`。

**Interfaces:** 使用子进程调用 `validate-agent.py`；通过可选的 `AGENT_CREATOR_VALIDATOR` 环境变量指定原版或新版脚本，不修改待测脚本。

- [x] 编写原始坏输入、合法输入、批量输入与路径重叠的测试。
- [x] 对原脚本运行，保留实际失败和通过数量，单独说明新增模式尚不存在。
- [x] 新版完成后，用同一批输入回归。

## Task 2: 有限的字段与文件检查

**Files:** `skills/agent-creator-codex/scripts/validate-agent.py`。

**Interfaces:** `validate_file(path, names, result, kind="standalone")`；CLI 保留多个路径与 `--strict`，增加 `--kind standalone|role-layer`。

- [x] 用集中字段表检查文本与稳定枚举；reasoning effort 仅检查非空字符串。
- [x] 检查 features/skills 类型、裁剪语义、skill selector 和 nickname 元数据。
- [x] 用明确诊断处理不可读取文件、UTF-8、TOML、错误容器；继续其余文件。
- [x] 按真实路径去重，按规范化后的角色名称检查不同文件的冲突。
- [x] 将未知字段标记为未覆盖/待核对，避免把小白名单冒充完整 Codex Schema。
- [x] 运行回归测试，确认没有新增第三方依赖。

## Task 3: 技能内容与交付证据

**Files:** 技能 `SKILL.md`、三个 `references/*.md`、示例 TOML、仓库 README、测试工作流、来源/审查文档。

**Interfaces:** 技能使用校验器真实参数；示例使用继承模型的默认写法。文档说明 static/load/runtime 三种检查的边界。

- [x] 精简 SKILL.md 的重复参考内容，保留实际执行步骤和阅读入口。
- [x] 修正上下文继承、指令层级和过期参数说明。
- [x] 对示例文件执行严格检查，对 Markdown 中的 TOML 示例执行语法检查。
- [x] 在隔离任务目录做一次独立使用验证；不向验证者泄露预期答案。
- [x] 记录实际运行环境和未执行的内部 Codex 验证。
- [x] 将优化结果提交到 AiLac/UsefulSkill，回读提交内容确认上传结果。
