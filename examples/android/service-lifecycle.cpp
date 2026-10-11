#include "webrtc_streamer.h"
#include <android/log.h>

// Call these functions when starting and stopping video playback.
// Execute on a background thread; let start finish before mounting the player.
int start_video_service() {
    __android_log_print(ANDROID_LOG_INFO, "WRS-App", "library=%s", wrs_version());
    int result = wrs_start(8000);
    if (result < 0) {
        __android_log_print(ANDROID_LOG_ERROR, "WRS-App", "start failed: %s", wrs_last_error());
    }
    // Return the error to the caller; never throw a C++ exception into JNI.
    return result;
}

// First disconnect the Vue player, then stop on a background thread, then
// allow library unload. Do not dlclose while any library call is still running.
void stop_video_service() {
    wrs_stop();
}
