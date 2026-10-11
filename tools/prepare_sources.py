"""Download pinned upstream sources into this workspace, never into a user cache."""
from pathlib import Path
import os
import hashlib
import json
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = ROOT / "downloads"
SOURCES = {
    "upstream": ("mpromonet/webrtc-streamer", "741ce34d28445ca3761296e80170e74270d2d2b6"),
    "upstream/civetweb": ("civetweb/civetweb", "d7ba35bbb649209c66e582d5a0244ba988a15159"),
    "upstream/cxxopts": ("jarro2783/cxxopts", "929bf2de375dba6f3a24a3a8fe681389b2b58a5b"),
    "upstream/html": ("mpromonet/webrtc-streamer-html", "fdef439b585d445f899d0df3002562c42847d30d"),
    "upstream/live555helper": ("mpromonet/live555helper", "121e0186153e647388bedd39964129c985b85019"),
    "upstream/prometheus-cpp": ("jupp0r/prometheus-cpp", "c9ffcdda9086ffd9e1283ea7a0276d831f3c8a8d"),
}


def download(url, target):
    if target.is_file():
        return
    partial = target.with_suffix(target.suffix + ".part")
    print(f"Downloading {url}", flush=True)
    with urllib.request.urlopen(url, timeout=60) as response, partial.open("wb") as output:
        while data := response.read(1024 * 1024):
            output.write(data)
    partial.replace(target)


def main():
    DOWNLOADS.mkdir(exist_ok=True)
    manifest = {}
    for relative, (repo, revision) in SOURCES.items():
        archive = DOWNLOADS / f"{repo.rsplit('/', 1)[1]}-{revision}.tar.gz"
        url = f"https://codeload.github.com/{repo}/tar.gz/{revision}"
        download(url, archive)
        with archive.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        destination = ROOT / relative
        marker = destination / ".source-revision"
        if marker.exists():
            if marker.read_text().strip() != revision:
                raise RuntimeError(f"Unexpected source revision in {destination}")
        else:
            destination.mkdir(parents=True, exist_ok=True)
            with tarfile.open(archive) as contents:
                for member in contents:
                    pieces = member.name.split("/", 1)
                    if len(pieces) < 2 or not pieces[1]:
                        continue
                    member.name = pieces[1]
                    contents.extract(member, path=destination, filter="data")
            marker.write_text(revision + "\n")
        manifest[relative] = {"repository": repo, "revision": revision, "url": url, "sha256": digest}
        print(f"Ready: {relative}", flush=True)
    (ROOT / "sources.lock.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
