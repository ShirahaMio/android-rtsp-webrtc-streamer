#ifndef ANDROID_WEBRTC_STREAMER_H
#define ANDROID_WEBRTC_STREAMER_H

#if defined(__GNUC__)
#define WRS_API __attribute__((visibility("default")))
#else
#define WRS_API
#endif

#ifdef __cplusplus
extern "C" {
#endif

/* One server per process. Call on a background thread, never the Android UI
 * thread. Returns 0 on success, 1 when already running on the same port,
 * -1 on failure (see wrs_last_error()). Listens on 127.0.0.1 only.
 * Ports must be 1024..65535. This build forwards encoded RTSP video.
 */
WRS_API int wrs_start(int port);
/* Stops HTTP requests, PeerConnections and RTSP workers, then joins threads.
 * Safe to call repeatedly. Keep the library loaded until this returns. */
WRS_API void wrs_stop(void);
WRS_API int wrs_is_running(void);
/* Per-calling-thread error; valid until the next start/stop on that thread. */
WRS_API const char* wrs_last_error(void);
WRS_API const char* wrs_version(void);

#ifdef __cplusplus
}
#endif
#endif
