# UsefulSkill

可直接使用、可以检查来源和验证记录的 Codex 技能。

## agent-creator-codex

帮助 Codex 创建和修正自定义子代理，检查 TOML 格式、常用字段和会被忽略的角色设置。默认继承模型与推理强度，也允许明确指定内部模型 ID。

- [技能说明与使用方式](skills/agent-creator-codex/README.md)
- [SKILL.md](skills/agent-creator-codex/SKILL.md)
- [审查判断、问题证据与改动取舍](docs/agent-creator-codex-review.md)
- [已执行的验证与适用边界](docs/validation-report.md)

将 `skills/agent-creator-codex/` 整个目录放入目标 Codex 支持的技能目录，然后在任务中使用 `$agent-creator-codex`。技能安装路径以目标版本文档为准；项目技能目录与输出的 `.codex/agents/` 角色目录用途不同。

校验器也可以独立使用，需要 Python 3.11+，不需要安装第三方包：

```bash
python skills/agent-creator-codex/scripts/validate-agent.py skills/agent-creator-codex/assets/case-analyst.toml --strict
python -m unittest discover -s tests -v
```

静态检查通过不证明目标 Codex 已加载角色，也不证明模型可调用或权限符合预期。真实调用需要在目标环境中验证。

## 来源与许可

本仓库初始为空，本次仅引入并优化 `agent-creator-codex`。该技能基于 [CowboyLogic/ai-dev](https://github.com/CowboyLogic/ai-dev/tree/7376c94c1a991acf965eeb7c01c2a15dc4c5e7e1/skills/agent-creator-codex)，保留 [MIT 许可](LICENSE)；修改范围见 [来源说明](skills/agent-creator-codex/NOTICE.md)。
