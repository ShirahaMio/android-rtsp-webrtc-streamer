# Include this snippet from src/main/cpp/CMakeLists.txt after creating your
# existing application target. The binary belongs in src/main/jniLibs/arm64-v8a/.
add_library(webrtc_streamer SHARED IMPORTED)
set_target_properties(webrtc_streamer PROPERTIES
    IMPORTED_LOCATION "${CMAKE_CURRENT_LIST_DIR}/../jniLibs/${ANDROID_ABI}/libwebrtc_streamer.so"
    INTERFACE_INCLUDE_DIRECTORIES "${CMAKE_CURRENT_LIST_DIR}/include")
# Replace existing_target with your real target:
# target_link_libraries(existing_target PRIVATE webrtc_streamer)
