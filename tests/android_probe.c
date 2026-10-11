#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

// Standalone Android shell diagnostic, no JNI and no plugin dependencies.
int main(int argc, char** argv) {
    setbuf(stdout, NULL);
    if (argc != 2) {
        fprintf(stderr, "Usage: %s /absolute/path/libwebrtc_streamer.so\n", argv[0]);
        return 2;
    }
    puts("PROBE 1: dlopen");
    void* lib = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (!lib) { fprintf(stderr, "LOAD FAILED: %s\n", dlerror()); return 3; }
    int (*start)(int) = (int (*)(int))dlsym(lib, "wrs_start");
    void (*stop)(void) = (void (*)(void))dlsym(lib, "wrs_stop");
    int (*running)(void) = (int (*)(void))dlsym(lib, "wrs_is_running");
    const char* (*error)(void) = (const char* (*)(void))dlsym(lib, "wrs_last_error");
    const char* (*version)(void) = (const char* (*)(void))dlsym(lib, "wrs_version");
    if (!start || !stop || !running || !error || !version) {
        fputs("MISSING EXPORT\n", stderr); return 4;
    }
    printf("PROBE 2: %s\n", version());
    for (int i = 0; i < 3; ++i) {
        printf("PROBE 3: start cycle %d on 18080\n", i + 1);
        int result = start(18080);
        if (result < 0) {
            fprintf(stderr, "START FAILED: %s\n", error()); stop(); return 5;
        }
        if (!running()) { fputs("NOT RUNNING\n", stderr); stop(); return 6; }
        puts("PROBE 4: ready, waiting 2 seconds");
        sleep(2);
        stop();
        if (running()) { fputs("STOP FAILED\n", stderr); return 7; }
        puts("PROBE 5: stopped");
    }
    // Keep the library loaded until process exit, as recommended for plugins.
    puts("PASS Android load/start/stop; RTSP and WebView not tested");
    return 0;
}
