# 安装与基本使用

## 系统要求

- Windows 10 22H2 或 Windows 11，x64；需要 Microsoft Edge WebView2 Runtime（通常已经随系统安装）。
- macOS 13 Ventura 或更高版本，Apple Silicon（M 系列芯片）。
- 约 500 MiB 可用空间，以及保存媒体所需的额外空间。

官方安装包已包含 Python sidecar、前端、yt-dlp、FFmpeg 和 ffprobe，不需要另行安装 Node.js、Python 或 Homebrew。

## 选择并启动应用

按 [README](../README.md#1-从-releases-下载) 选择架构并校验 SHA-256。Windows 可以安装 `.msi`/NSIS `.exe`，或完整解压 `Bilidown-<版本>-windows-x64-portable.zip` 后运行 `Bilidown.exe`。便携版必须保留同目录的 `bilidown-backend.exe`、许可证说明和 FFmpeg 来源说明；不要从压缩包预览窗口直接运行。macOS 保留完整 `Bilidown.app`。

启动后会显示原生桌面窗口，内部后端使用随机本地端口并仅监听 `127.0.0.1`。关闭主窗口会隐藏到系统托盘，而不是中断下载。托盘菜单可重新打开窗口或彻底退出。

## 定位媒体

输入以下任一种凭据：

- `BV1ACNJ6VEwP`
- `av170001`
- `https://www.bilibili.com/video/BV...`
- `https://b23.tv/...`
- `https://www.bilibili.com/bangumi/play/...`
- `https://space.bilibili.com/.../favlist`
- `https://live.bilibili.com/...`

番剧、课程、收藏夹、合集、系列、播放列表、稍后再看、空间投稿/音频、动态、互动视频、直播和 BiliIntl 等覆盖范围见[媒体支持矩阵](media-support.md)。

## 选择与下载

1. 解析后确认标题、UP 主、封面和分 P。
2. 单选、多选或全选分 P。链接带 `?p=2` 时默认选择对应分 P。
3. 选择输出目录。默认是用户“下载”目录下的 `Bilidown`。
4. 创建封面、音频、视频、字幕或弹幕任务。批量预览和任务最多 100 项，超过 20 项时需要再次确认。
5. 普通任务按顺序执行；单项失败不会阻止后续条目，结果会标为“部分完成”并列出失败项。
6. 直播使用独立录制器，可“停止并保留”当前 `.ts` 文件，或“取消并删除”临时文件。

单独下载一个分 P 时文件名仅包含主标题与 BV 号；一次下载多 P 时才增加 `Pxx` 与分 P 标题。同名文件不会覆盖，应用会自动追加序号。

## 结束应用

关闭主窗口只会隐藏到系统托盘。默认空闲 30 分钟自动退出，可在托盘选择 15/30/60 分钟或关闭自动退出；退出前 5 分钟会提醒。普通任务或直播录制活动期间不会自动退出。彻底退出会清理内存 Cookie、任务记录和未保留的临时文件。

## 便携版说明

Windows 便携版不写注册表、不安装服务或开机启动项；下载目录仍由你在界面中选择。如果双击后没有显示窗口，请先安装 Microsoft Edge WebView2 Evergreen Runtime，再重试。解压目录可以移动，但不能只复制 `Bilidown.exe`，必须一起保留所有文件。
