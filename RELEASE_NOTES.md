# v1.0 — Android9+ ARM64 RTSP → WebRTC

Android RTSP → WebRTC 动态库，基于 mpromonet/webrtc-streamer 移植。

- Android API28+ / arm64-v8a，C API、JNI 和 Vue2 示例。
- 进程内 localhost 服务，无需另起外部 RTSP→WebRTC 转换服务器。
- 普通 ELF RELA 重定位，修正旧 Houdini 环境加载兼容路径。
- 用户于 2026-10-11 确认服务启动正常且视频可以播放；未提供最终设备明细。
- 已执行符号/初始化审计和同源码 Linux 启停、H.264 媒体链路测试。
- H.265 依赖 WebView 协商支持，无转码；不承诺所有设备或长期运行均已验证。

下载 Assets 中的二进制 ZIP，集成说明见 README。
libwebrtc_streamer.so SHA256：`d5c70120445775f7916bc0ca6bfa80e7c19ec5524985400f6366a9226bf630ca`
