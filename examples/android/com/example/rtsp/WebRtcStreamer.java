package com.example.rtsp;

/** Call start/stop from a background executor owned by the host plugin. */
public final class WebRtcStreamer {
    static { System.loadLibrary("webrtc_streamer"); }
    private WebRtcStreamer() {}

    public static void start(int port) {
        int result = nativeStart(port);
        if (result < 0) throw new IllegalStateException(nativeLastError());
    }

    public static void stop() { nativeStop(); }
    public static boolean isRunning() { return nativeIsRunning(); }

    private static native int nativeStart(int port);
    private static native void nativeStop();
    private static native boolean nativeIsRunning();
    private static native String nativeLastError();
}
