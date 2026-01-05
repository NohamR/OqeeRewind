#!/usr/bin/env python3
import argparse
import subprocess
import re

def hhmmss_to_seconds(time_str):
    """Convert hh:mm:ss to total seconds."""
    parts = list(map(int, time_str.split(':')))
    if len(parts) == 3:
        h, m, s = parts
    elif len(parts) == 2:
        h = 0
        m, s = parts
    elif len(parts) == 1:
        h = 0
        m = 0
        s = parts[0]
    else:
        raise ValueError("Invalid time format")
    return h * 3600 + m * 60 + s

def get_video_duration(filename):
    """Return video duration in seconds using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of",
        "default=noprint_wrappers=1:nokey=1", filename
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())

def trim_video(input_file, output_file, remove_start=None, remove_end=None):
    # Convert times to seconds
    start_sec = hhmmss_to_seconds(remove_start) if remove_start else 0
    duration = None
    if remove_end:
        total_duration = get_video_duration(input_file)
        end_sec = hhmmss_to_seconds(remove_end)
        duration = total_duration - start_sec - end_sec
        if duration <= 0:
            raise ValueError("Trim times are too long; resulting duration is <= 0")
    
    cmd = ["ffmpeg", "-y"]
    if start_sec > 0:
        cmd += ["-ss", str(start_sec)]
    cmd += ["-i", input_file]
    if duration:
        cmd += ["-t", str(duration)]
    cmd += ["-c", "copy", output_file]

    print("Running command:", " ".join(cmd))
    subprocess.run(cmd, check=True)

def main():
    parser = argparse.ArgumentParser(description="Trim video start/end times")
    parser.add_argument("input_file", help="Input video file")
    parser.add_argument("output_file", help="Output trimmed video file")
    parser.add_argument("--remove-start", help="Time to remove from start (hh:mm:ss)")
    parser.add_argument("--remove-end", help="Time to remove from end (hh:mm:ss)")
    args = parser.parse_args()

    trim_video(args.input_file, args.output_file, args.remove_start, args.remove_end)

if __name__ == "__main__":
    main()