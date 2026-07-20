Bilidown Windows x64 Portable
==============================

版本：1.0.0
作者与发布者：Arsvine Zhu
版权：Copyright © 2026 Arsvine Zhu

使用方式
--------

1. 将整个压缩包解压到一个可写入的本地目录；不要直接在压缩包预览窗口中运行。
2. 双击 Bilidown.exe 启动。请保留 bilidown-backend.exe、SHA256SUMS.txt、
   THIRD_PARTY_NOTICES.txt 和 FFMPEG_SOURCE.txt 与主程序处于同一目录。
3. 关闭主窗口只会隐藏到系统托盘。可从托盘重新打开程序，或选择“彻底退出”。

系统要求
--------

- Windows 10 22H2 或 Windows 11，x64。
- Microsoft Edge WebView2 Runtime。Windows 10/11 通常已预装；若窗口无法启动，请从
  Microsoft 安装 WebView2 Evergreen Runtime 后重试。
- 无需安装 Python、Node.js 或 FFmpeg。

便携版不会安装服务、配置开机启动或写入注册表。应用的下载输出由你在界面中自行选择。
只下载你有权保存的内容，并遵守 Bilibili 服务条款与适用版权法律。

校验
----

Release 中的同名 .zip.sha256 用于校验整个压缩包；SHA256SUMS.txt 用于校验解压后的
运行文件。PowerShell 示例：Get-FileHash .\Bilidown.exe -Algorithm SHA256。
