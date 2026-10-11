    // live555 delivers individual NALs. Combine slices with the same presentation
    // timestamp before handing one complete picture to WebRTC. One-frame latency.
    std::vector<uint8_t> m_h264AccessUnit;
    int64_t m_h264Timestamp = 0;
    bool m_h264Key = false;

    void onH264Data(unsigned char* buffer, ssize_t size, int64_t ts,
                    const std::string& codec) {
        if (size <= 0) return;
        if (!m_h264AccessUnit.empty() && ts != m_h264Timestamp) {
            auto frame = webrtc::EncodedImageBuffer::Create(
                m_h264AccessUnit.data(), m_h264AccessUnit.size());
            PostFrame(frame, m_h264Timestamp, m_h264Key
                ? webrtc::VideoFrameType::kVideoFrameKey
                : webrtc::VideoFrameType::kVideoFrameDelta);
            m_h264AccessUnit.clear();
            m_h264Key = false;
        }
        for (const auto& index : webrtc::H264::FindNaluIndices(
                 std::span<const uint8_t>(buffer, size))) {
            if (index.payload_size == 0) continue;
            auto type = webrtc::H264::ParseNaluType(buffer[index.payload_start_offset]);
            const auto* begin = buffer + index.start_offset;
            const auto* end = buffer + index.payload_start_offset + index.payload_size;
            if (type == webrtc::H264::NaluType::kSps) {
                m_cfg.assign(begin, end);
                auto sps = webrtc::SpsParser::ParseSps(std::span<const uint8_t>(
                    buffer + index.payload_start_offset + 1, index.payload_size - 1));
                postFormat(codec, sps ? sps->width : 0, sps ? sps->height : 0);
            } else if (type == webrtc::H264::NaluType::kPps) {
                // Avoid unbounded growth if a source repeats PPS without SPS.
                if (m_cfg.size() + (end - begin) < 65536)
                    m_cfg.insert(m_cfg.end(), begin, end);
            } else if (type == webrtc::H264::NaluType::kIdr ||
                       type == webrtc::H264::NaluType::kSlice) {
                if (m_h264AccessUnit.empty()) {
                    m_h264Timestamp = ts;
                    m_h264Key = type == webrtc::H264::NaluType::kIdr;
                    if (m_h264Key) m_h264AccessUnit = m_cfg;
                }
                if (m_h264AccessUnit.size() + (end - begin) > 16 * 1024 * 1024) {
                    m_h264AccessUnit.clear();
                    m_h264Key = false;
                    return;
                }
                m_h264AccessUnit.insert(m_h264AccessUnit.end(), begin, end);
            }
        }
    }

