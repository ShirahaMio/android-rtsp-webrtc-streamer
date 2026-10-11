#pragma once
#include <vector>
#include "api/video_codecs/sdp_video_format.h"

// Android's software-H264 build flag is disabled; encoded-frame forwarding
// must advertise formats independently of the software encoder factory.
inline std::vector<webrtc::SdpVideoFormat> PassthroughFormats() {
  std::vector<webrtc::SdpVideoFormat> formats;
  for (const char* profile : {"42e01f", "42001f", "4d001f", "64001f"}) {
    formats.emplace_back("H264", webrtc::CodecParameterMap{
        {"profile-level-id", profile}, {"level-asymmetry-allowed", "1"},
        {"packetization-mode", "1"}});
  }
  // Negotiated only when the receiving WebView advertises H265. This does not
  // provide transcoding or add H265 decoding support to Android WebView.
  formats.emplace_back("H265", webrtc::CodecParameterMap{
      {"profile-id", "1"}, {"tier-flag", "0"}, {"level-id", "93"}, {"tx-mode", "SRST"}});
  return formats;
}
