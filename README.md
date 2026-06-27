# Karaoke

A simple webapp that turns an audio track into a karaoke song.

## Features

- sessions -- can start a session with a unique join link
- playback view with visuals and lyrics
- enqueue menu to:
  - specify a youtube url to pull a track from
  - file upload a mp3 or wav file of a track
  - pick a track from the linked jellyfin library
  - reorder already-queued tracks

## How it works

When a track is enqueued via the enqueue menu:

1. (youtube url only) it is downloaded via ytdl (https://github.com/ytdl-org/youtube-dl)
1. https://pypi.org/project/pyacoustid/ is used to identify the original track
1. the file is stemmed w/ [demucs](https://github.com/adefossez/demucs) or [spleeter](https://github.com/deezer/spleeter), then joined with the vocal stem at 20% initial volume
1. timed lyrics for the track are fetched with the ytdl (can be specified), but results from https://lrclib.net/ (fetched via acoustic id) are prioritized if available
1. at playback time, the web-browser is sent the lyrics and starts streaming the audio file from the server
1. if the lyrics are in the lrclib format, they are shown according to playback timing, otherwise the lyrics are displayed in full in a scrollable view

Websockets to keep all views up-to-date (queue updates, track transitions)
