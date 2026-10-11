# 构建 v1.0

使用 Linux x86_64（例如 Ubuntu24.04 / WSL2），Python3.12+、Git、CMake、Ninja、Clang
及 WebRTC 构建依赖。建议可用磁盘至少 60GB，内存 16GB 以上。Android 依赖下载需要网络。

```bash
export WRS_BUILD_ROOT=/path/on/build-disk/android-build
mkdir -p "$WRS_BUILD_ROOT"
bash tools/bootstrap_webrtc.sh
bash tools/build_android.sh
bash tools/build_android_probe.sh
python3 tools/collect_licenses.py
```

工作目录路径可以自选；WSL 用户应将 Linux 虚拟磁盘和交换文件放在期望的磁盘上。
如需代理，运行前自行设置 http_proxy/https_proxy；脚本不会配置系统代理。
首次 WebRTC 同步量较大。原构建环境的测试位置标签 hook 曾受 Python 镜像网络限制失败；
它不属于本库编译目标，但首次配置仍需确保工具链 hooks 完成后再执行 GN/Ninja。

构建结果：dist/arm64-v8a/libwebrtc_streamer.so、dist/include/webrtc_streamer.h。
脚本执行 API28 与初始化入口审计，记录在 logs/。发布二进制校验值见 RELEASE_NOTES.md。
相对本机原始脚本，仓库脚本已把路径改为 WRS_BUILD_ROOT 和仓库相对路径；
目录参数化经语法检查，但尚未在全新 Linux 环境完整重建。

## 本地运行回归

```bash
bash tools/build_host_test.sh
python3 tests/smoke_runtime.py "$WRS_BUILD_ROOT/webrtc/src/out/linux-smoke/libwebrtc_streamer.so"
```

媒体测试另需 ffmpeg、Python aiortc/aiohttp/av，以及将 MediaMTX 放入
$WRS_BUILD_ROOT/media-test/mediamtx；测试源码 tests/media_roundtrip.py 使用本地合成流。
这些 Linux 测试不能代替 Android 设备实际运行验证。
