"""Generate an original 20-second silent video fixture; no third-party footage.
One-time tooling: uv pip install imageio-ffmpeg
"""
from pathlib import Path
import os
import subprocess
import imageio_ffmpeg

out = Path(os.environ.get('CLUB_MEDIA_OUTPUT', str(Path(__file__).resolve().parents[1] / 'instance' / 'media' / 'fixture.webm')))
out.parent.mkdir(parents=True, exist_ok=True)
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-f', 'lavfi', '-i',
    'testsrc2=duration=20:size=960x540:rate=24', '-c:v', 'libvpx-vp9', '-b:v', '350k', '-an', str(out)], check=True)
print(out)
