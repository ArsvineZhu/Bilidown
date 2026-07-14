# 安装与基本使用

## 系统要求

- Windows 10 22H2 或 Windows 11，x64。
- macOS 13 Ventura 或更高版本，Apple Silicon 或 Intel。
- 约 500 MiB 可用空间，以及保存媒体所需的额外空间。

便携包已包含 Python、前端、yt-dlp、FFmpeg 和 ffprobe，不需要安装 Node.js、Python 或 Homebrew。

## 选择并启动应用

按 [README](../README.md#1-从-releases-下载) 选择架构并校验 SHA-256。必须先完整解压：Windows 保留整个 `Bilidown` 文件夹；macOS 保留完整 `Bilidown.app`。

启动后，应用选择随机本地端口并打开浏览器。地址应以 `http://127.0.0.1:` 开头。令牌只用于本次启动，并会从地址栏移除。不要把首次打开的完整地址发给别人。

## 定位视频

输入以下任一种凭据：

- `BV1ACNJ6VEwP`
- `av170001`
- `https://www.bilibili.com/video/BV...`
- `https://b23.tv/...`

首版仅支持普通 UP 主 UGC 投稿及其分 P，不支持番剧、直播、课程、收藏夹批量下载或互动视频分支。

## 选择与下载

1. 解析后确认标题、UP 主、封面和分 P。
2. 单选、多选或全选分 P。链接带 `?p=2` 时默认选择对应分 P。
3. 选择输出目录。默认是用户“下载”目录下的 `Bilidown`。
4. 分别创建封面、音频或视频任务。任务按顺序单并发执行。
5. 观察百分比、速度、ETA 和结果路径；运行中可取消，失败或取消后可重试。

单独下载一个分 P 时文件名仅包含主标题与 BV 号；一次下载多 P 时才增加 `Pxx` 与分 P 标题。同名文件不会覆盖，应用会自动追加序号。

## 结束应用

关闭浏览器标签页不会终止本地服务。Windows 使用任务管理器结束 `Bilidown.exe`；macOS 使用活动监视器结束 `Bilidown`。退出后内存 Cookie 会话和任务记录立即清除，已下载文件不会删除。
