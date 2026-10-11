"""Host-only end-to-end test: synthetic H264 -> RTSP -> library -> WebRTC.

Uses FFmpeg, a local MediaMTX test server and aiortc; never contacts a camera.
"""
import asyncio
import ctypes
import json
from pathlib import Path
import os
import socket
import subprocess
import sys
import time
from urllib.parse import urlencode

import aiohttp
import av
from aiortc import RTCConfiguration, RTCPeerConnection, RTCRtpSender, RTCSessionDescription
from aiortc.sdp import candidate_from_sdp

WORKSPACE = Path(__file__).resolve().parents[1]
TEST_ROOT = Path(os.environ.get('WRS_BUILD_ROOT', '/opt/android-build')) / 'media-test'
LIB = ctypes.CDLL(sys.argv[1])
LIB.wrs_start.argtypes = [ctypes.c_int]
LIB.wrs_start.restype = ctypes.c_int
LIB.wrs_stop.restype = None
LIB.wrs_last_error.restype = ctypes.c_char_p


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


async def receive_once(session, base, rtsp_url, peerid):
    pc = RTCPeerConnection(RTCConfiguration(iceServers=[]))
    done = asyncio.get_running_loop().create_future()
    received = []
    tasks = []

    @pc.on('track')
    def on_track(track):
        async def consume():
            try:
                while len(received) < 30:
                    frame = await track.recv()
                    assert (frame.width, frame.height) == (640, 360)
                    received.append(frame.pts)
                    if len(received) == 30:
                        with av.open(str(WORKSPACE / f'logs/{peerid}.png'), 'w', format='image2') as output:
                            stream = output.add_stream('png', rate=1)
                            stream.width, stream.height = frame.width, frame.height
                            stream.pix_fmt = 'rgb24'
                            frame.pts = None
                            for packet in stream.encode(frame):
                                output.mux(packet)
                            for packet in stream.encode():
                                output.mux(packet)
                if not done.done():
                    done.set_result(len(received))
            except Exception as error:
                if not done.done():
                    done.set_exception(error)
        tasks.append(asyncio.create_task(consume()))

    transceiver = pc.addTransceiver('video', direction='recvonly')
    transceiver.setCodecPreferences([c for c in RTCRtpSender.getCapabilities('video').codecs
                                    if c.mimeType.lower() == 'video/h264'])
    try:
        await pc.setLocalDescription(await pc.createOffer())
        params = urlencode({'peerid': peerid, 'url': rtsp_url, 'options': 'rtptransport=tcp&timeout=5'})
        async with session.post(base + '/api/call?' + params,
                                json={'type': pc.localDescription.type, 'sdp': pc.localDescription.sdp}) as response:
            text = await response.text()
            assert response.status == 200, text
            answer = json.loads(text)
        assert answer['type'] == 'answer'
        assert 'H264' in answer['sdp']
        await pc.setRemoteDescription(RTCSessionDescription(**answer))
        known = set()
        for _ in range(20):
            async with session.get(base + '/api/getIceCandidate?' + urlencode({'peerid': peerid})) as response:
                response.raise_for_status()
                candidates = await response.json(content_type=None)
            for item in candidates or []:
                raw = item['candidate']
                if raw in known:
                    continue
                known.add(raw)
                candidate = candidate_from_sdp(raw.removeprefix('candidate:'))
                candidate.sdpMid = item.get('sdpMid')
                candidate.sdpMLineIndex = item.get('sdpMLineIndex')
                await pc.addIceCandidate(candidate)
            if pc.connectionState == 'connected' or done.done():
                break
            await asyncio.sleep(0.2)
        count = await asyncio.wait_for(done, timeout=25)
        assert len(set(received)) > 1, 'Video timestamps did not advance'
        return {'peerid': peerid, 'frames': count, 'resolution': '640x360',
                'codec': 'H264', 'connection_state': pc.connectionState,
                'remote_ice_candidates': len(known)}
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await pc.close()
        async with session.get(base + '/api/hangup?' + urlencode({'peerid': peerid})) as response:
            await response.read()


async def main():
    TEST_ROOT.mkdir(exist_ok=True)
    rtsp_port, http_port = free_port(), free_port()
    config = TEST_ROOT / 'mediamtx.yml'
    config.write_text(f'''logLevel: warn
rtspAddress: 127.0.0.1:{rtsp_port}
rtspTransports: [tcp]
rtmp: false
hls: false
webrtc: false
srt: false
paths:
  camera: {{}}
''')
    rtsp_url = f'rtsp://127.0.0.1:{rtsp_port}/camera'
    base = f'http://127.0.0.1:{http_port}'
    children = []
    files = []
    try:
        media_log = (WORKSPACE / 'logs/mediamtx-test.log').open('w')
        files.append(media_log)
        server = subprocess.Popen([str(TEST_ROOT / 'mediamtx'), str(config)], stdout=media_log, stderr=subprocess.STDOUT)
        children.append(server)
        for _ in range(50):
            if server.poll() is not None:
                raise RuntimeError('MediaMTX failed; inspect mediamtx-test.log')
            try:
                with socket.create_connection(('127.0.0.1', rtsp_port), timeout=0.1):
                    break
            except OSError:
                await asyncio.sleep(0.1)
        encoder_log = (WORKSPACE / 'logs/ffmpeg-test.log').open('w')
        files.append(encoder_log)
        encoder = subprocess.Popen([
            'ffmpeg', '-hide_banner', '-loglevel', 'warning', '-re', '-f', 'lavfi',
            '-i', 'testsrc2=size=640x360:rate=15', '-an', '-c:v', 'libx264',
            '-profile:v', 'baseline', '-level:v', '3.1', '-pix_fmt', 'yuv420p',
            '-preset', 'ultrafast', '-tune', 'zerolatency', '-g', '15', '-bf', '0',
            '-x264-params', 'slices=4',
            '-f', 'rtsp', '-rtsp_transport', 'tcp', rtsp_url],
            stdout=encoder_log, stderr=subprocess.STDOUT)
        children.append(encoder)
        await asyncio.sleep(1.5)
        assert encoder.poll() is None, 'FFmpeg publisher exited'
        assert LIB.wrs_start(http_port) == 0, LIB.wrs_last_error()
        results = []
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
            # Reconnect after hangup exercises stream disposal and recreation.
            for index in range(2):
                result = await receive_once(session, base, rtsp_url, f'roundtrip-{index}')
                results.append(result)
                print('PASS', json.dumps(result), flush=True)
        (WORKSPACE / 'logs/media-test-results.json').write_text(json.dumps({
            'platform': 'Linux x86_64 host build of the same source',
            'android_device_tested': False, 'results': results}, indent=2) + '\n')
    finally:
        LIB.wrs_stop()
        for child in reversed(children):
            child.terminate()
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        for file in files:
            file.close()


asyncio.run(main())
