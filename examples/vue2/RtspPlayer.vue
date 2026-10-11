<template>
  <section>
    <video ref="video" autoplay muted playsinline controls></video>
    <p v-if="error" role="alert">{{ error }}</p>
  </section>
</template>

<script>
// Copy the supplied official webrtcstreamer.js beside this component.
import WebRtcStreamer from './webrtcstreamer.js'

export default {
  props: {
    rtspUrl: { type: String, required: true },
    serviceUrl: { type: String, default: 'http://127.0.0.1:8000' }
  },
  data () { return { error: '' } },
  mounted () {
    this.destroyedPlayer = false
    this.player = null
    this.connect()
  },
  watch: {
    rtspUrl () { this.connect() },
    serviceUrl () { this.connect() }
  },
  beforeDestroy () {
    this.destroyedPlayer = true
    this.connectionGeneration = (this.connectionGeneration || 0) + 1
    if (this.player) this.player.disconnect()
  },
  methods: {
    async connect () {
      const generation = this.connectionGeneration = (this.connectionGeneration || 0) + 1
      if (this.player) this.player.disconnect()
      this.error = ''
      if (!this.rtspUrl) return
      try {
        if (typeof RTCPeerConnection === 'undefined') {
          throw new Error('宿主 WebView 不支持 WebRTC')
        }
        const response = await fetch(this.serviceUrl + '/health')
        if (!response.ok) throw new Error('本地视频服务未就绪')
        const health = await response.json()
        if (health.status !== 'ready') throw new Error('本地视频服务未就绪')
        if (this.destroyedPlayer || generation !== this.connectionGeneration) return
        this.player = new WebRtcStreamer(this.$refs.video, this.serviceUrl)
        this.player.onError = () => { this.error = '视频连接失败，请检查视频编码、网络与服务日志' }
        this.player.connect(this.rtspUrl, '', 'rtptransport=tcp&timeout=10')
      } catch (error) {
        if (!this.destroyedPlayer && generation === this.connectionGeneration) {
          this.error = error.message
        }
      }
    }
  }
}
</script>

<style scoped>
video { width: 100%; background: #000; }
</style>
