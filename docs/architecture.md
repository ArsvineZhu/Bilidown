# 架构说明

Bilidown 是单进程、本地优先的 Web 应用。Python 负责安全边界、解析和下载，React 只展示非敏感结构化数据。

## 组件

- `backend/bilidown/`：FastAPI、输入规范化、Cookie 会话、yt-dlp 引擎、任务队列、安全中间件和运行时发现。
- `frontend/src/`：React + TypeScript 单页界面、API 客户端、登录状态、媒体选择和 SSE 任务进度。
- `packaging/`：PyInstaller spec、FFmpeg 准备、Windows/macOS 构建、许可证与便携冒烟。
- `tests/` 与 `frontend/e2e/`：后端、媒体、文档、浏览器和显式网络测试。

## 数据流

1. 启动器选择本地端口和随机令牌，启动 Uvicorn 后打开浏览器。
2. `/api/resolve` 规范化 BV/AV/URL，通过 yt-dlp 获取分 P 和格式；签名媒体 URL 在后端终止。
3. 前端按精确格式 ID 与登录来源创建任务。
4. 单并发 `JobManager` 在线程中下载，SSE 返回脱敏进度。
5. FFmpeg 仅负责无重编码封装或明确选择的 MP3 转码，最终文件以防覆盖方式移动。

## 状态与生命周期

任务、Cookie 会话和令牌都不持久化。应用重启后队列为空；下载结果由文件系统负责保存。任务状态只允许 queued → running → completed/failed/cancelled，失败和取消可创建新的重试任务。

## 平台边界

业务代码保持跨平台；`runtime.py` 发现 PyInstaller 根目录和 FFmpeg，`app.py` 调用平台文件管理器，`packaging/entrypoint.py` 提供原生启动错误提示。PyInstaller 在 Windows、macOS arm64 和 macOS x86_64 原生构建，不能交叉生成目标包。
