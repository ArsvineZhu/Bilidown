# 贡献指南

感谢改进 Bilidown。第一次使用 GitHub 也可以按下面步骤操作。

## 报告问题

先搜索现有 Issues。新问题应包含系统版本、Bilidown 版本、可复现步骤、预期/实际结果和脱敏日志。界面问题请附截图；删除用户名、完整路径、Cookie、`SESSDATA` 和签名媒体 URL。安全问题不要公开，改用 [SECURITY.md](SECURITY.md) 的渠道。

## 准备代码

1. 在 GitHub 点击 **Fork**，把副本放到自己的账号。
2. `git clone https://github.com/<你的账号>/Bilidown.git`。
3. 创建分支：`git switch -c feat/short-description`。
4. 按[开发环境](docs/development.md)安装依赖并先运行现有测试。

不要提交 `.venv/`、`.tools/`、`dist/`、`build/`、`output/`、浏览器配置或下载媒体。依赖升级必须说明原因并更新对应锁文件。

## 修改与测试

保持变更聚焦，复用现有模型、服务和组件。Python 使用 4 空格与 `snake_case`；React/TypeScript 使用 2 空格、命名导出和 `PascalCase` 组件。新增行为应配套 `test_*.py`、`*.test.tsx` 或 Playwright 测试。

提交前运行：

```powershell
.venv\Scripts\python -m pytest
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend build
pnpm --dir frontend test:e2e
```

macOS 将 Python 路径替换为 `.venv/bin/python`。

## Commit 与 Pull Request

本仓库尚无可继承的历史约定，因此新提交采用 Conventional Commits：`feat:`、`fix:`、`docs:`、`test:`、`build:`、`ci:`、`chore:`。主题使用祈使语气并保持单一目的。

PR 应说明目的、主要变化、验证命令、未验证风险和关联 Issue。界面变化附前后截图；构建变化列出已实际测试的平台。保持 PR 可审阅，不夹带无关格式化或重构。
