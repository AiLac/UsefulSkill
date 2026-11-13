# 来源与修改说明

本技能基于 CowboyLogic/ai-dev 的 `skills/agent-creator-codex`，按 MIT 许可使用和修改。

- 上游仓库：https://github.com/CowboyLogic/ai-dev
- 固定提交：`7376c94c1a991acf965eeb7c01c2a15dc4c5e7e1`
- 原校验脚本 blob：`18c82f57f0dcb0ad7c47c7272071906cfad59c34`
- 原版权：Copyright (c) 2025-2026 CowboyLogic
- 许可全文：[LICENSE](LICENSE)

2026-11-13 的修改包括：按官方 `rust-v0.167.2` 源码核对角色规则；补充字段类型与部分枚举检查；修复无效编码和错误容器导致的崩溃；对输入路径去重；区分独立角色与显式注册的配置层；移除文件名和指令长度的风格阻断；精简文档并补充中文说明、回归测试和验证证据。

本项目为独立维护的衍生版本，不是 OpenAI 官方技能。源码核对与静态测试不代表在所有 Codex 版本、模型供应商或内部发行版上验证通过。
