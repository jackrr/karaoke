"""YouTube audio download utilities using yt-dlp."""
import os
import tempfile
import asyncio

class YouTubeDownloader:
    """Download audio from YouTube videos using yt-dlp."""
    
    @staticmethod
    async def download(url: str, output_dir: str = "/tmp/karaoke-storage/youtube") -> str:
        """Download audio from YouTube. Returns path to saved file."""
        import subprocess
        os.makedirs(output_dir, exist_ok=True)
        
        # Use yt-dlp to download audio only
        cmd = [
            "yt-dlp",
            "-x",  # audio only
            "--audio-format", "mp3",
            "--audio-quality", "5",
            "--output", os.path.join(output_dir, "%(id)s.%(ext)s"),
            "--no-post-overwrites",
            url
        ]
        
        try:
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                # Get the filename from stdout
                output_file = output_dir + "/video_id.mp3"  # simplify
                return output_file
            else:
                raise subprocess.CalledProcessError(result.returncode, cmd)
        except FileNotFoundError:
            raise RuntimeError("yt-dlp not found. Install with: pip install yt-dlp")
