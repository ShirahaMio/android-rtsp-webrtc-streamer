#include "webrtc_streamer.h"

#include <atomic>
#include <future>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <string>
#include <thread>
#ifdef __ANDROID__
#include <android/log.h>
#endif

#include "PeerConnectionManager.h"
#include "HttpServerRequestHandler.h"
#include "rtc_base/ssl_adapter.h"
#include "rtc_base/thread.h"

namespace {
std::mutex lifecycle_mutex;
std::thread service_thread;
// Written before the startup promise, cleared after joining service_thread.
webrtc::Thread* event_thread = nullptr;
std::atomic<bool> running{false};
int active_port = 0;
thread_local std::string last_error;
std::once_flag ssl_once;
bool ssl_ready = false;

void stage(const char* message) {
#ifdef __ANDROID__
  __android_log_print(ANDROID_LOG_INFO, "WRS", "%s", message);
#else
  (void)message;
#endif
}

void serve(int port, std::promise<std::string> ready) {
  bool announced = false;
  stage("02 service thread entered");
  try {
    webrtc::ThreadManager::Instance()->WrapCurrentThread();
    stage("03 WebRTC thread attached");
    std::call_once(ssl_once, [] {
      webrtc::LoggingConfig log_config;
      log_config.set_debug_severity(webrtc::LS_WARNING);
      log_config.set_log_prefix("webrtc-streamer");
      webrtc::InitializeLogging(std::move(log_config));
      ssl_ready = webrtc::InitializeSSL();
    });
    if (!ssl_ready) throw std::runtime_error("WebRTC SSL initialization failed");
    stage("04 SSL initialized");
    event_thread = webrtc::Thread::Current();
    {
      const std::list<std::string> ice_servers; // Local playback needs no public STUN.
      const Json::Value streams(Json::objectValue);
      stage("05 constructing peer manager");
      PeerConnectionManager manager(
          ice_servers, streams, webrtc::AudioDeviceModule::kDummyAudio,
          "rtsp://", "0:65535", true, false, 4,
          webrtc::PeerConnectionInterface::kAll, "",
          "WebRTC-FrameDropper/Disabled/WebRTC-Video-H26xPacketBuffer/Enabled/");
      stage("06 initializing peer factories");
      if (!manager.InitializePeerConnection())
        throw std::runtime_error("PeerConnection factory initialization failed");

      std::vector<std::string> options{
          "listening_ports", "127.0.0.1:" + std::to_string(port),
          "num_threads", "4", "enable_directory_listing", "no",
          "enable_keep_alive", "yes", "keep_alive_timeout_ms", "1000",
          "request_timeout_ms", "10000", "decode_url", "no",
          "access_control_allow_origin", "*"};
      auto api = manager.getHttpApi();
      // A cheap readiness check that does not disclose camera credentials.
      api["/health"] = [](const mg_request_info*, const Json::Value&) {
        Json::Value body;
        body["status"] = "ready";
        body["version"] = wrs_version();
        return std::make_tuple(200, std::map<std::string, std::string>{}, body);
      };
      stage("07 starting localhost HTTP");
      HttpServerRequestHandler http(api, options);
      running.store(true);
      ready.set_value("");
      announced = true;
      stage("08 service ready");
      event_thread->Run();
      running.store(false);
      // http is destroyed first and joins its workers before manager teardown.
    }
  } catch (const std::exception& error) {
    stage(error.what());
    running.store(false);
    if (!announced) ready.set_value(error.what());
  } catch (...) {
    running.store(false);
    if (!announced) ready.set_value("Unexpected server initialization failure");
  }
  webrtc::ThreadManager::Instance()->UnwrapCurrentThread();
  // SSL is process-wide in this private WebRTC copy. Keep it initialized across
  // start/stop cycles instead of interfering with other native TLS users.
}
}  // namespace

extern "C" int wrs_start(int port) {
  stage("01 wrs_start entered: android-rtsp-bridge/1.0-api28");
  std::lock_guard<std::mutex> lock(lifecycle_mutex);
  last_error.clear();
  if (port < 1024 || port > 65535) {
    last_error = "Port must be in 1024..65535";
    return -1;
  }
  if (running.load()) {
    if (active_port == port) return 1;
    last_error = "Server already running on another port; stop it first";
    return -1;
  }
  if (service_thread.joinable()) service_thread.join();
  event_thread = nullptr;
  try {
    std::promise<std::string> ready;
    auto result = ready.get_future();
    service_thread = std::thread(serve, port, std::move(ready));
    last_error = result.get();
    if (!last_error.empty()) {
      service_thread.join();
      event_thread = nullptr;
      return -1;
    }
    active_port = port;
    return 0;
  } catch (const std::exception& error) {
    last_error = error.what();
    if (service_thread.joinable()) service_thread.join();
    event_thread = nullptr;
    return -1;
  }
}

extern "C" void wrs_stop() {
  stage("09 wrs_stop entered");
  std::lock_guard<std::mutex> lock(lifecycle_mutex);
  last_error.clear();
  if (running.load() && event_thread) event_thread->Quit();
  if (service_thread.joinable()) service_thread.join();
  event_thread = nullptr;
  active_port = 0;
  running.store(false);
  stage("10 service stopped");
}

extern "C" int wrs_is_running() { return running.load() ? 1 : 0; }
extern "C" const char* wrs_last_error() { return last_error.c_str(); }
extern "C" const char* wrs_version() {
  return "android-rtsp-bridge/1.0-api28 upstream/741ce34 webrtc/848836f";
}
