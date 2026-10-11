#include <jni.h>
#include "webrtc_streamer.h"

extern "C" JNIEXPORT jint JNICALL
Java_com_example_rtsp_WebRtcStreamer_nativeStart(JNIEnv*, jclass, jint port) {
  return wrs_start(port);
}
extern "C" JNIEXPORT void JNICALL
Java_com_example_rtsp_WebRtcStreamer_nativeStop(JNIEnv*, jclass) { wrs_stop(); }
extern "C" JNIEXPORT jboolean JNICALL
Java_com_example_rtsp_WebRtcStreamer_nativeIsRunning(JNIEnv*, jclass) {
  return wrs_is_running() ? JNI_TRUE : JNI_FALSE;
}
extern "C" JNIEXPORT jstring JNICALL
Java_com_example_rtsp_WebRtcStreamer_nativeLastError(JNIEnv* env, jclass) {
  return env->NewStringUTF(wrs_last_error());
}
