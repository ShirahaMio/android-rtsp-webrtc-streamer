"""Stage the pinned sources and explicit Android patches inside WebRTC's GN tree."""
from pathlib import Path
import os
import hashlib
import json
import shutil
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def change(path, old, new):
    content = path.read_text()
    if content.count(old) != 1:
        raise RuntimeError(f"Patch context not unique: {path}: {old[:70]!r}")
    path.write_text(content.replace(old, new))


def main():
    src = Path(sys.argv[1]).resolve()
    if not (src / "webrtc.gni").is_file():
        raise RuntimeError("Expected a WebRTC source checkout")
    target = src / "rtsp_bridge"
    target.mkdir(exist_ok=True)
    for name in ("inc", "src", "live555helper", "civetweb"):
        shutil.copytree(ROOT / "upstream" / name, target / name, dirs_exist_ok=True)
    shutil.copytree(ROOT / "android" / "include", target / "include", dirs_exist_ok=True)
    shutil.copytree(ROOT / "android" / "src", target / "android_src", dirs_exist_ok=True)
    shutil.copyfile(ROOT / "android/overrides/HttpServerRequestHandler.h", target / "inc/HttpServerRequestHandler.h")
    shutil.copyfile(ROOT / "android/exports.map", target / "exports.map")
    archive = ROOT / "downloads/live555.tar.gz"
    expected = json.loads((ROOT / "downloads/live555.json").read_text())["sha256"]
    with archive.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
            raise RuntimeError("live555 checksum mismatch")
    with tarfile.open(archive) as contents:
        # Upstream testProgs contains absolute symlinks to the author's samples.
        # Only extract ordinary files/directories needed for this library.
        allowed = {"groupsock", "liveMedia", "UsageEnvironment", "BasicUsageEnvironment"}
        for member in contents:
            parts = Path(member.name).parts
            if not (member.isfile() or member.isdir()):
                continue
            if len(parts) >= 2 and parts[0] == "live" and (parts[1] in allowed or parts[1].startswith("COPYING")):
                contents.extract(member, target, filter="data")

    capturer = target / "inc/CapturerFactory.h"
    change(capturer, '#include "VcmCapturer.h"',
           '#ifndef WRS_RTSP_ONLY\n#include "VcmCapturer.h"\n#endif')
    change(capturer, '\t\tif (std::regex_match("videocap://",publishFilter) && !useNullCodec) {',
           '#ifndef WRS_RTSP_ONLY\n\t\tif (std::regex_match("videocap://",publishFilter) && !useNullCodec) {')
    change(capturer, '\t\tif (std::regex_match("v4l2://",publishFilter) && useNullCodec) {',
           '#endif\n\t\tif (std::regex_match("v4l2://",publishFilter) && useNullCodec) {')
    change(capturer, '\t\t\tvideoSource = TrackSource<VcmCapturer>::Create(videourl, opts, videoDecoderFactory);',
           '#ifndef WRS_RTSP_ONLY\n\t\t\tvideoSource = TrackSource<VcmCapturer>::Create(videourl, opts, videoDecoderFactory);\n#endif')

    for name in ("VideoEncoderFactory", "VideoDecoderFactory"):
        path = target / "inc" / (name + ".h")
        change(path, "#pragma once", '#pragma once\n#include "PassthroughFormats.h"')
        change(path, "supported_formats_(webrtc::SupportedH264Codecs())", "supported_formats_(PassthroughFormats())")
        # The shared helper already advertises H265 with explicit parameters.
        content = path.read_text()
        content = "\n".join(line for line in content.splitlines() if "supported_formats_.push_back" not in line) + "\n"
        path.write_text(content)

    for name, member_type, member in (
        ("NullEncoder.h", "webrtc::EncodedImageCallback*", "m_encoded_image_callback"),
        ("NullDecoder.h", "webrtc::DecodedImageCallback*", "m_decoded_image_callback"),
    ):
        change(target / "inc" / name, f"{member_type} {member};", f"{member_type} {member} = nullptr;")
    change(target / "inc/livevideosource.h", "uint64_t                           m_prevTimestamp;",
           "uint64_t                           m_prevTimestamp = 0;")
    video_path = target / "inc/livevideosource.h"
    video_content = video_path.read_text()
    start = video_content.index("    void onH264Data(")
    end = video_content.index("    void onH265Data(", start)
    video_path.write_text(video_content[:start] +
                         (ROOT / "android/overrides/h264_access_unit.inc").read_text() +
                         video_content[end:])
    env_header = target / "live555helper/inc/environment.h"
    change(env_header, "Environment(char& stop);", "Environment(EventLoopWatchVariable& stop);")
    change(env_header, "char& m_stop;", "EventLoopWatchVariable& m_stop;")
    change(env_header, "char  m_stopRef;", "EventLoopWatchVariable m_stopRef{0};")
    change(target / "live555helper/src/environment.cpp", "Environment::Environment(char & stop)",
           "Environment::Environment(EventLoopWatchVariable & stop)")
    change(target / "inc/livevideosource.h", "char        m_stop;", "EventLoopWatchVariable m_stop{0};")
    change(target / "inc/liveaudiosource.h", "char m_stop;", "EventLoopWatchVariable m_stop{0};")
    for name in ("livevideosource.h", "liveaudiosource.h"):
        path = target / "inc" / name
        content = path.read_text()
        # Stop the scheduler and join it before manipulating its RTSP client.
        import re
        content, count = re.subn(
            r"m_liveclient\.stop\(\);\s*m_env\.stop\(\);\s*m_capturethread\.join\(\);",
            "m_env.stop();\n        m_capturethread.join();\n        m_liveclient.stop();", content)
        if count != 1:
            raise RuntimeError(f"Unexpected capture shutdown in {path}")
        path.write_text(content)
    change(target / "inc/VideoDecoder.h", "#include <chrono>", "#include <chrono>\n#include <atomic>")
    change(target / "inc/VideoDecoder.h", "bool                                  m_stop;", "std::atomic<bool>                     m_stop;")

    header = target / "inc/PeerConnectionManager.h"
    change(header, "\t\tbool InitializePeerConnection();", """
        bool InitializePeerConnection();
        void scheduleHangup(const std::string& peerid) {
            if (!m_shuttingDown.load()) {
                m_cleanupThread->PostTask([this, peerid] {
                    if (!m_shuttingDown.load()) hangUp(peerid);
                });
            }
        }
""")
    detached = '''\t\t\t\t\t\tstd::thread([this]() {
\t\t\t\t\t\t\tm_peerConnectionManager->hangUp(m_peerid);
\t\t\t\t\t\t}).detach();'''
    change(header, detached, "\t\t\t\t\t\tm_peerConnectionManager->scheduleHangup(m_peerid);")
    change(header, "\t\tconst webrtc::Environment                                                    m_webrtcenv;",
           "\t\tstd::unique_ptr<webrtc::Thread> m_cleanupThread;\n\t\tstd::atomic<bool> m_shuttingDown{false};\n\t\tconst webrtc::Environment                                                    m_webrtcenv;")
    change(header, "std::atomic<webrtc::PeerConnectionInterface::IceGatheringState> m_gatheringState;",
           "std::atomic<webrtc::PeerConnectionInterface::IceGatheringState> m_gatheringState{webrtc::PeerConnectionInterface::kIceGatheringNew};")
    manager = target / "src/PeerConnectionManager.cpp"
    change(manager, "#include <ifaddrs.h>", """#ifdef WEBRTC_ANDROID
#include "rtc_base/ifaddrs_android.h"
using webrtc::getifaddrs;
using webrtc::freeifaddrs;
#else
#include <ifaddrs.h>
#endif""")
    change(manager, ": m_webrtcenv(", ": m_cleanupThread(webrtc::Thread::Create()), m_webrtcenv(")
    change(manager, '\tm_workerThread->SetName("worker", NULL);',
           '\tm_cleanupThread->SetName("rtsp-cleanup", nullptr);\n\tm_cleanupThread->Start();\n\tm_workerThread->SetName("worker", NULL);')
    change(manager, "m_extraHost(resolveHostnameToIp(extraHost))", 'm_extraHost(extraHost.empty() ? "" : resolveHostnameToIp(extraHost))')
    old_destructor = '''PeerConnectionManager::~PeerConnectionManager() {
\tstd::map<std::string, std::unique_ptr<PeerConnectionObserver>> peers;
\t{
\t\tstd::lock_guard<std::mutex> peerlock(m_peerMapMutex);
\t\tpeers.swap(m_peer_connectionobs_map);
\t}

\tm_workerThread->BlockingCall([this] {
\t\tm_audioDeviceModule->Release();
    });\t
}'''
    new_destructor = '''PeerConnectionManager::~PeerConnectionManager() {
    m_shuttingDown.store(true);
    m_cleanupThread->Stop();
    std::map<std::string, std::unique_ptr<PeerConnectionObserver>> peers;
    {
        std::lock_guard<std::mutex> lock(m_peerMapMutex);
        peers.swap(m_peer_connectionobs_map);
    }
    peers.clear();
    m_stream_map.clear();
    m_builtin_peer_connection_factory = nullptr;
    m_null_peer_connection_factory = nullptr;
    m_workerThread->BlockingCall([this] {
        if (m_audioDeviceModule) m_audioDeviceModule->Terminate();
        m_audioDeviceModule = nullptr;
    });
}'''
    change(manager, old_destructor, new_destructor)

    sources = ["src/PeerConnectionManager.cpp", "src/rtspvideocapturer.cpp",
               "src/rtspaudiocapturer.cpp", "src/rtpvideocapturer.cpp",
               "src/filevideocapturer.cpp", "src/fileaudiocapturer.cpp",
               "android_src/webrtc_streamer.cpp", "android_src/http_server.cpp",
               "civetweb/src/civetweb.c", "civetweb/src/CivetServer.cpp"]
    sources += [p.relative_to(target).as_posix() for p in sorted((target / "live555helper/src").glob("*.cpp"))]
    for folder in ("groupsock", "liveMedia", "UsageEnvironment", "BasicUsageEnvironment"):
        sources += [p.relative_to(target).as_posix() for p in sorted((target / "live" / folder).iterdir()) if p.suffix in (".c", ".cpp")]
    build = (ROOT / "android/BUILD.gn.in").read_text()
    build = build.replace("@SOURCES@", "\n".join(f'    "{name}",' for name in sources))
    (target / "BUILD.gn").write_text(build)
    print(f"Prepared {target}: {len(sources)} sources, Android patches applied")


if __name__ == "__main__":
    main()
