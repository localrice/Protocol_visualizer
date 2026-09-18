"""Streaming activity functionality.

The workflow remains simulated until a real public manifest is configured.
"""

from __future__ import annotations

from protocol import event


def simulated_stream(quality: str) -> dict:
    quality = quality if quality in {"auto", "360p", "720p", "1080p"} else "auto"
    representation = {"auto": "adaptive", "360p": "360p", "720p": "720p", "1080p": "1080p"}[quality]
    paths = ["/video/manifest.mpd", "/video/segment_001.m4s", "/video/segment_002.m4s", "/video/segment_003.m4s"]
    events = [
        event(1, "DNS", "client-to-server", "query", "DNS Query: A media.example.com", {"Name": "media.example.com", "Type": "A", "Resolver": "Recursive Resolver (simulated)", "Traffic": "Simulated"}),
        event(2, "DNS", "server-to-client", "response", "DNS Response: NOERROR", {"Status": "resolved", "Answer": "203.0.113.20", "Traffic": "Simulated"}),
    ]
    sequence = 3
    for path in paths:
        kind = "Manifest / Playlist" if path.endswith(".mpd") else "Media Segment"
        events.append(event(sequence, "MANIFEST" if path.endswith(".mpd") else "SEGMENT", "client-to-server", "request", f"GET {path} HTTP/1.1", {
            "Host": "media.example.com", "Representation": representation, "Resource": kind, "Traffic": "Simulated"
        }))
        events.append(event(sequence + 1, "HTTP", "server-to-client", "response", "HTTP/1.1 200 OK", {
            "Content-Type": "application/dash+xml" if path.endswith(".mpd") else "video/iso.segment",
            "Resource": kind, "Traffic": "Simulated"
        }))
        sequence += 2
    return {"success": True, "activity": "streaming", "events": events, "simulated": True}
