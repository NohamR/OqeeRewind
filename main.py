"""Main module for Oqee channel selection and stream management."""

import os
import sys
import argparse
import asyncio
import subprocess
import shutil
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from utils.input import (
    stream_selection,
    get_date_input,
    get_epg_data_at,
    select_program_from_epg,
    get_selection,
)
from utils.oqee import OqeeClient
from utils.downloader import get_keys
from utils.utilities import verify_cmd, merge_segments, decrypt, verify_mp4ff
from utils.times import (
    convert_date_to_sec,
    convert_sec_to_ticks,
    convert_ticks_to_sec,
    convert_sec_to_date,
    find_nearest_tick_by_hour,
    bruteforce,
)
from utils.stream import save_segments, get_kid, get_init
from utils.logging_config import setup_logging, logger

load_dotenv()
TIMESCALE = 90000
DURATION = 288000


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Oqee TV Live Downloader")

    parser.add_argument(
        "--start-date",
        type=str,
        help="Start date and time in YYYY-MM-DD HH:MM:SS format",
    )
    parser.add_argument(
        "--end-date", type=str, help="End date and time in YYYY-MM-DD HH:MM:SS format"
    )
    parser.add_argument(
        "--duration",
        type=str,
        help="Duration in HH:MM:SS format (alternative to --end-date)",
    )
    parser.add_argument("--channel-id", type=str, help="Channel ID to download from")
    parser.add_argument(
        "--video",
        type=str,
        help="Video quality selection (e.g., 'best', '1080p', '720p', '1080p+best', '720p+worst')",
    )
    parser.add_argument(
        "--audio", type=str, help="Audio track selection (e.g., 'best', 'fra_main')"
    )
    parser.add_argument(
        "--title",
        type=str,
        help="Title for the download (default: channel_id_start_date)",
    )
    parser.add_argument("--username", type=str, help="Oqee username for authentication")
    parser.add_argument("--password", type=str, help="Oqee password for authentication")
    parser.add_argument(
        "--key",
        action="append",
        help="DRM key for decryption (can be specified multiple times)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./downloads",
        help="Output directory for downloaded files (default: ./downloads)",
    )
    parser.add_argument(
        "--widevine-device",
        type=str,
        default="./widevine/device.wvd",
        help="Path to Widevine device file (default: ./widevine/device.wvd)",
    )
    parser.add_argument(
        "--bruteforce-batch-size",
        type=int,
        default=20000,
        help="Batch size for bruteforce (default: 20000)",
    )
    parser.add_argument(
        "--segment-batch-size",
        type=int,
        default=64,
        help="Batch size for segment downloads (default: 64)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level (default: INFO)",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    setup_logging(level=getattr(logging, args.log_level.upper()))
    verify_mp4ff()

    # Check if CLI mode
    cli_mode = any(
        [
            args.start_date,
            args.end_date,
            args.duration,
            args.channel_id,
            args.video,
            args.audio,
            args.title,
            args.username,
            args.password,
            args.key,
        ]
    )

    try:
        if cli_mode:
            # CLI mode
            logger.info("Running in CLI mode...")

            # Parse dates
            start_date = None
            end_date = None

            if args.start_date:
                try:
                    start_date = datetime.strptime(args.start_date, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    logger.error("Invalid start-date format. Use YYYY-MM-DD HH:MM:SS")
                    sys.exit(1)

            if args.end_date and args.duration:
                logger.error("Cannot specify both --end-date and --duration")
                sys.exit(1)
            elif args.end_date:
                try:
                    end_date = datetime.strptime(args.end_date, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    logger.error("Invalid end-date format. Use YYYY-MM-DD HH:MM:SS")
                    sys.exit(1)
            elif args.duration and start_date:
                # Parse duration HH:MM:SS
                try:
                    h, m, s = map(int, args.duration.split(":"))
                    duration_td = timedelta(hours=h, minutes=m, seconds=s)
                    end_date = start_date + duration_td
                except ValueError:
                    logger.error("Invalid duration format. Use HH:MM:SS")
                    sys.exit(1)

            if not start_date:
                logger.error("start-date is required in CLI mode")
                sys.exit(1)
            if not end_date:
                logger.error("Either end-date or duration is required in CLI mode")
                sys.exit(1)

            keys = args.key or []
            # END_SUFFIX = ".".join([args.video, args.audio]) if args.video and args.audio else ""
            END_SUFFIX = ""
            title = (
                args.title + END_SUFFIX
                or f"{args.channel_id}_{start_date.strftime('%Y%m%d_%H%M%S') + END_SUFFIX}"
            )

            # Get stream selections
            selections = get_selection(args.channel_id, args.video, args.audio)
            if not selections:
                logger.error("Error during stream selection.")
                sys.exit(1)

            logger.debug("Start date: %s", start_date)
            logger.debug("End date: %s", end_date)
            logger.debug("Channel ID: %s", args.channel_id)
            logger.debug("Video quality: %s", args.video)
            logger.debug("Audio track: %s", args.audio)
            logger.debug("Title: %s", title)
            logger.debug("DRM keys: %s", keys)
            logger.debug("Output dir: %s", args.output_dir)
            logger.debug("Widevine device: %s", args.widevine_device)
            logger.debug("Batch size: %d", args.bruteforce_batch_size)

        else:
            # Interactive mode
            selections = stream_selection()
            freebox_id = selections.get("channel", {}).get("freebox_id")
            channel_id = selections.get("channel", {}).get("id")
            title = None
            start_date, end_date = get_date_input()

            if start_date > datetime.now() - timedelta(days=7):
                epg_data = get_epg_data_at(start_date)

                programs = epg_data["entries"][str(channel_id)]
                program_selection = select_program_from_epg(
                    programs, start_date, end_date
                )
                if program_selection:
                    start_date = program_selection["start_date"]
                    end_date = program_selection["end_date"]
                    title = program_selection["title"]

            title = title or f"{freebox_id}_{start_date.strftime('%Y%m%d_%H%M%S')}"
            keys = []

        batch_size = args.bruteforce_batch_size if cli_mode else 20000
        segment_batch_size = args.segment_batch_size if cli_mode else 64
        output_dir = os.getenv("OUTPUT_DIR") or (
            args.output_dir if cli_mode else "./downloads"
        )

        start_tick_user = int(
            convert_sec_to_ticks(convert_date_to_sec(start_date), TIMESCALE)
        )

        video_data = None
        audio_data = None

        for content_type, sel in [
            ("video", selections["video"]),
            ("audio", selections["audio"]),
        ]:
            start_tick_manifest = sel["segments"]["timeline"][0]["t"]
            manifest_date = convert_sec_to_date(
                convert_ticks_to_sec(start_tick_manifest, TIMESCALE)
            )
            init_segment = sel["segments"]["initialization"]
            track_id = init_segment.split("/")[-1].split("_init")[0]

            if start_date.date() == manifest_date.date():
                logger.info(
                    "Date match between requested start date and manifest data, proceeding with download..."
                )

                start_tick, start_rep = find_nearest_tick_by_hour(
                    start_tick_manifest, start_date, TIMESCALE, DURATION
                )
                end_tick, end_rep = find_nearest_tick_by_hour(
                    start_tick_manifest, end_date, TIMESCALE, DURATION
                )
            else:
                logger.info(
                    "Date mismatch between requested start date and manifest data for %s, bruteforce method is needed.", content_type
                )

                valid_ticks = asyncio.run(bruteforce(track_id, start_tick_user, batch_size))
                if len(valid_ticks) == 0:
                    logger.error("No valid ticks found in bruteforce range.")
                    sys.exit(1)
                valid_tick = valid_ticks[0]

                start_tick, start_rep = find_nearest_tick_by_hour(
                    valid_tick, start_date, TIMESCALE, DURATION
                )
                end_tick, end_rep = find_nearest_tick_by_hour(
                    valid_tick, end_date, TIMESCALE, DURATION
                )

            rep_nb = (end_tick - start_tick) // DURATION + 1
            logger.info("Total segments to fetch for %s: %d", content_type, rep_nb)
            data = {
                "start_tick": start_tick,
                "rep_nb": rep_nb,
                "track_id": track_id,
                "selection": sel,
            }
            if content_type == "video":
                video_data = data
            else:
                audio_data = data

        missing_keys = []
        for content_type, data in [("video", video_data), ("audio", audio_data)]:
            os.makedirs(output_dir, exist_ok=True)
            track_id = data["track_id"]
            start_tick = data["start_tick"]
            rep_nb = data["rep_nb"]
            asyncio.run(
                save_segments(output_dir, track_id, start_tick, rep_nb, DURATION, batch_size=segment_batch_size)
            )

            # Merge video and audio
            video_file = f"{output_dir}/temp_video.mp4"
            audio_file = f"{output_dir}/temp_audio.mp4"

            data["file"] = video_file if content_type == "video" else audio_file
            merge_segments(
                output_dir,
                track_id,
                video_file if content_type == "video" else audio_file,
            )

            kid = get_kid(output_dir, track_id)
            data["kid"] = kid
            key = None
            for k in keys:
                if k.split(":")[0] == kid:
                    key = k
                    break
            if not key:
                logger.info("No key found for KID %s, need to fetch it.", kid)
                missing_keys.append(kid)

        if len(missing_keys) > 0:
            method = {}
            API_URL = os.getenv("API_URL") or None
            API_KEY = os.getenv("API_KEY") or None
            if API_URL and API_KEY:
                method = {"method": "api", "api_url": API_URL, "api_key": API_KEY}
            else:
                username = args.username or os.getenv("OQEE_USERNAME")
                password = args.password or os.getenv("OQEE_PASSWORD")
                client = OqeeClient(username, password)
                verify_cmd(args.widevine_device)
                method = {
                    "method": "device",
                    "device_file": args.widevine_device,
                    "client_class": client,
                }

            fetched_keys = get_keys(kids=missing_keys, method=method)
            logger.info("Fetched keys: %s", fetched_keys)
            keys = keys + fetched_keys

        for content_type, data in [("video", video_data), ("audio", audio_data)]:
            track_id = data["track_id"]
            file = data["file"]
            kid = data["kid"]

            key = None
            for k in keys:
                if k.split(":")[0] == kid:
                    key = k
                    break

            init_path = get_init(output_dir, track_id)
            dec_file = f"{output_dir}/dec_{content_type}.mp4"
            decrypt(file, init_path, dec_file, key)

        track_id_video = video_data["track_id"]
        track_id_audio = audio_data["track_id"]
        start_tick_video = video_data["start_tick"]
        start_tick_audio = audio_data["start_tick"]
        diff_start = start_tick_audio - start_tick_video
        diff_start_sec = convert_ticks_to_sec(diff_start, TIMESCALE)

        # ffmpeg -i "concat:init.mp4|merged_dec.m4s" -c copy output.mp4
        command_ffmpeg = (
            f'ffmpeg -i "concat:{output_dir}/segments_{track_id_video}/init.mp4|'
            f'{output_dir}/dec_video.mp4" -c copy {output_dir}/video.mp4'
        )
        logger.debug("FFmpeg command: %s", command_ffmpeg)
        subprocess.run(
            command_ffmpeg,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        command_ffmpeg = (
            f'ffmpeg -i "concat:{output_dir}/segments_{track_id_audio}/init.mp4|'
            f'{output_dir}/dec_audio.mp4" -c copy {output_dir}/audio.mp4'
        )

        logger.debug("FFmpeg command: %s", command_ffmpeg)
        subprocess.run(
            command_ffmpeg,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )

        COMMAND_MERGE = (
            f"ffmpeg -i {output_dir}/video.mp4 -itsoffset {diff_start_sec} "
            f"-i {output_dir}/audio.mp4 -c copy -map 0:v -map 1:a {output_dir}/output.mp4"
        )
        logger.debug("Merge command: %s", COMMAND_MERGE)
        subprocess.run(
            COMMAND_MERGE,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )

        FINAL_OUTPUT = f"{output_dir}/{title}.mp4"
        shutil.move(f"{output_dir}/output.mp4", FINAL_OUTPUT)
        logger.info("Final output saved to %s", FINAL_OUTPUT)

        os.remove(f"{output_dir}/dec_video.mp4")
        os.remove(f"{output_dir}/dec_audio.mp4")
        os.remove(f"{output_dir}/video.mp4")
        os.remove(f"{output_dir}/audio.mp4")
        os.remove(f"{output_dir}/temp_video.mp4")
        os.remove(f"{output_dir}/temp_audio.mp4")
        shutil.rmtree(f"{output_dir}/segments_{video_data['track_id']}")
        shutil.rmtree(f"{output_dir}/segments_{audio_data['track_id']}")

    except KeyboardInterrupt:
        logger.info("\n\nProgram interrupted by user. Goodbye!")


# uv run python main.py --start-date "2025-01-01 12:00:00" --duration "01:00:00" \
# --channel-id 536 --video "720+best" --audio best --title "Test" \
# --key 5b1288b31b6a3f789a205614bbd7fac7:14980f2578eca20d78bd70601af21458 \
# --key acacd48e12efbdbaa479b6d6dbf110b4:500af89b21d64c4833e107f26c424afb
# uv run python main.py --start-date "2025-12-19 12:00:00" --duration "00:01:00" \
# --channel-id 536 --video "720+best" --audio best --title "Test" \
# --key 5b1288b31b6a3f789a205614bbd7fac7:14980f2578eca20d78bd70601af21458 \
# --key acacd48e12efbdbaa479b6d6dbf110b4:500af89b21d64c4833e107f26c424afb
