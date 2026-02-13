# CLAUDE.md — 项目经验与教训

## 项目概述

nanobot 是一个 AI 助手框架，通过 Telegram 等渠道连接用户，使用 LLM（如 GPT-5.2）处理消息，支持技能（Skills）扩展。

## 关键架构

- **Gateway 是长驻进程**：`nanobot serve` 启动后，Python 代码加载到内存中运行。修改 .py 文件后必须重启 gateway 才能生效。SKILL.md 等数据文件每次请求都从磁盘读取，无需重启。
- **技能加载流程**：`loop.py` → `match_skills()` 匹配触发词 → `context.py` 注入 system prompt → `skills.py` 的 `load_skills_for_context()` 加载内容并替换 secrets
- **Session 历史**：存在 `~/.nanobot/sessions/` 下的 JSONL 文件中，只保存 user/assistant 文本消息，不保存 tool calls。失败的对话会影响后续 AI 行为。
- **工作空间**：配置中 `workspace: ~/.nanobot/workspace`，技能分为 workspace skills（优先）和 builtin skills（`nanobot/skills/`）

## 犯过的错误总结

### 1. 没有意识到 gateway 需要重启（最严重）

**错误**：修改了 `skills.py`、`web.py`、`loop.py` 后，直接让用户去 Telegram 测试，没有提醒重启 gateway。用户多次测试失败。

**教训**：修改 Python 代码（.py 文件）后，**必须提醒用户重启 `nanobot serve`**。只有 SKILL.md 等纯数据文件的修改不需要重启。

### 2. 过度依赖 AI 执行多步骤指令

**错误**：最初的方案要求 GPT-5.2 先调用 `read_file` 读取 token 文件，再将读到的值传入 `web_fetch` 的 headers。GPT-5.2 没有可靠执行这个两步流程——它要么跳过读取，要么读了但没正确传参。

**教训**：不要依赖 LLM 执行关键的多步操作。应该在系统层面自动化（如 secrets 自动注入），让 LLM 只需要做最简单的事。

### 3. 环境变量方案不适合 Windows + 长驻进程

**错误**：最初用环境变量 `$ITICK_TOKEN` 存储 token，但：
- `echo $ITICK_TOKEN` 是 Unix 语法，Windows 不支持
- 即使用 `os.environ.get()`，gateway 启动后新设的环境变量无法被已运行的进程读取
- 不同终端/进程的环境变量不互通

**教训**：在 Windows 上，用**文件**存储配置/密钥比环境变量更可靠。文件路径用 `~/.nanobot/` 下的固定位置。

### 4. 没有第一时间直接测试 API

**错误**：前几轮修改都是"改代码 → 让用户测试 → 看报错 → 再改"。浪费了多次迭代。

**教训**：遇到 API 认证问题，第一步应该用 `curl` 直接测试 API，确认 token 是否有效、需要哪些 headers。这样可以排除代码问题 vs API 问题。

### 5. Session 历史污染导致恶性循环

**错误**：每次失败的对话都保存在 session 中。AI 在后续对话中看到历史失败记录，会认为"token 不可用"而不再尝试，形成恶性循环。清理了多次 session 才解决。

**教训**：调试 API 认证问题时，每次修复后都要清空相关 session（`~/.nanobot/sessions/telegram_*.jsonl`），避免旧失败记录影响 AI 行为。

### 6. 方案迭代太多次

**错误**：Token 认证经历了 4 次方案迭代：
1. 环境变量 `$ITICK_TOKEN`（Unix 语法，失败）
2. Python exec 读取环境变量（进程隔离，失败）
3. `read_file` 读文件 + AI 两步操作（AI 不可靠，失败）
4. `_resolve_secrets` 自动注入（成功）

**教训**：应该更早分析根本原因（AI 执行多步骤不可靠），而不是在表面上反复修补。最佳方案是让系统自动处理，AI 零步骤参与。

### 7. 忽略了 accept header

**错误**：iTick API 文档明确要求 `accept: application/json` header，但最初的 SKILL.md 只写了 `token` header。虽然测试发现不带 accept 也能工作，但应该遵循官方文档。

**教训**：API 调用应严格按文档要求传所有 headers，不要假设某些是可选的。

## 开发规范

### 修改代码后的检查清单
1. 修改了 .py 文件？→ 提醒重启 gateway
2. 修改了 SKILL.md？→ 不需要重启，但要清空相关 session
3. 涉及 API 认证？→ 先用 curl 直接测试
4. 涉及 LLM 行为？→ 清空 session 历史再测试

### 文件位置速查
- 配置：`~/.nanobot/config.json`
- Token/密钥：`~/.nanobot/itick_token.txt`
- Session：`~/.nanobot/sessions/telegram_*.jsonl`
- 技能（内置）：`nanobot/skills/*/SKILL.md`
- 技能加载：`nanobot/agent/skills.py`
- 消息循环：`nanobot/agent/loop.py`
- 上下文构建：`nanobot/agent/context.py`
- Web 工具：`nanobot/agent/tools/web.py`

### Secrets 机制
技能可在 metadata 中声明 secrets 映射：
```
metadata: {"nanobot":{"secrets":{"KEY":"~/.nanobot/file.txt"}}}
```
内容中的 `{{KEY}}` 会在加载时自动替换为文件内容。限制只能读取 `~/.nanobot/` 下的文件。

### Windows 注意事项
- Python 路径用 `Path.expanduser()` 处理 `~`
- 不要用 `echo $VAR`，用 Python 的 `os.environ.get()`
- `asyncio.create_subprocess_shell` 继承父进程环境变量
- PowerShell 和 cmd 的引号规则不同，复杂命令建议写成 .py 文件执行
