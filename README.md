# Android RTSP → WebRTC Streamer

将 RTSP → WebRTC 服务嵌入 Android 应用或插件进程，配合 Vue2 / WebView 播放视频。
基于 [mpromonet/webrtc-streamer](https://github.com/mpromonet/webrtc-streamer) 的非官方 Android 移植，
不是上游官方发行版，也不隶属于 DJI。

## 下载与能力

在本仓库 **Releases → v0.4 → Assets** 下载 `webrtc-streamer-android9plus-arm64-v0.4.zip`。

- Android 9+（API 28），`arm64-v8a`，要求宿主进程为 64 位 ARM 或具有兼容的 ARM 转译能力。
- 在进程内启动 HTTP 信令服务，只监听 `127.0.0.1`；手机必须能直接访问 RTSP 源。
- 保留官方 `webrtcstreamer.js` 接口；提供 C API 和可选 JNI/Java 封装。
- H.264 编码帧透传；H.265 取决于接收端实际协商支持，不提供 H.265 → H.264 转码。
- 不采集手机摄像头或麦克风；不提供缩放、旋转、码率转换。音频尚未单独验证。
- 使用静态、隐藏的内部 C++ 运行库，无需额外附带 `libc++_shared.so`。

## 快速集成

1. 将 `.so` 放入模块 `src/main/jniLibs/arm64-v8a/`。
2. C++ 复制 `webrtc_streamer.h`，按 `examples/android/import-library.cmake` 导入并链接到插件目标。
3. 后台线程调用 `wrs_start(8000)`。0 表示启动成功，1 表示同端口已运行，-1 时在同线程读取 `wrs_last_error()`。
4. Vue2 沿用官方播放器：

```javascript
const player = new WebRtcStreamer(videoElement, 'http://127.0.0.1:8000')
player.connect(rtspUrl, '', 'rtptransport=tcp&timeout=10')
```

先断开前端播放器，再调用 `wrs_stop()`，等待结束后才能卸载插件。
若使用 Java 示例，保留 `com.example.rtsp.WebRtcStreamer` 包名和类名，合并混淆规则。
不要跨 C 接口传递 C++ 对象或让异常穿过 JNI 边界。

宿主 APK 需要 INTERNET 权限，WebView 必须允许访问本地 HTTP。
HTTPS 页面的混合内容策略及本地页面网络限制需要宿主配合，复制 `.so` 无法改变这些策略。
用 WebView 请求 `http://127.0.0.1:8000/health` 检查服务就绪。

## 验证状态

2026-10-11：使用者反馈 v0.4 服务启动正常，视频已能播放。反馈未明确最终设备型号、
Android 版本及模拟器/真机，不能据此宣称所有 Android9+ 设备均已验证。
本地验证覆盖 ARM64 编译、API28 符号兼容、初始化入口重定位，以及同源码 Linux
上的重复启停、四分片 H.264 RTSP → WebRTC 解码和断开重连。未进行长期稳定性认证。

## v0.4 兼容处理

API28 编译、emulated TLS、普通 ELF RELA 重定位，避免旧转译加载器对压缩重定位的兼容问题。
PAC/BTI 被关闭，compiler-rt CPU 初始化从源码重编译；这是兼容性取舍，减少了分支保护加固。
H.264 同时间戳分片合并为完整帧，增加约一帧缓冲。建议实时源使用无 B 帧编码。

## 源码与构建

见 [BUILDING.md](BUILDING.md)。`android/` 为封装，`tools/prepare_android_target.py` 明确应用
移植补丁；`upstream/` 保存固定版本上游源码，`sources.lock.json` 记录来源和校验值。
`downloads/live555.tar.gz` 是构建所需的固定第三方源码归档。
工具链、完整 WebRTC 依赖及中间产物需要另外下载，不包含在仓库中。

## 许可

新增 Android 封装与移植脚本采用 MIT，见 [LICENSE](LICENSE)。
第三方源码仍按各自原有许可证分发，见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
和 `licenses/`；这不是对整份二进制的统一 MIT 授权。
