# 第三方代码

根 LICENSE 仅覆盖新增封装/脚本，不替换第三方许可证。

- webrtc-streamer 与其上游移植代码：Unlicense，见 upstream/UNLICENSE。
- WebRTC 及其依赖：各自许可证，见 licenses/webrtc/。
- CivetWeb：见 licenses/civetweb-LICENSE.md。
- live555：LGPL，见 licenses/live555-COPYING 和 COPYING.LESSER；源码归档位于 downloads/。
- compiler-rt：Apache-2.0 WITH LLVM-exception，见 licenses/webrtc/third_party/compiler-rt/。

完整列表在 licenses/libraries.txt；固定源版本在 sources.lock.json 和构建脚本。
分发包含静态第三方组件的二进制时，需遵守各自的源码、修改及重新链接要求。
仓库提供所用移植源码、补丁、固定依赖位置与构建步骤，不能把整份 .so 当作仅受 MIT 管辖。
