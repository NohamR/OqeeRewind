"""Utility functions for time and tick conversions, and bruteforce operations."""
import asyncio
import datetime
import time

import aiohttp

from utils.stream import fetch_segment


def convert_ticks_to_sec(ticks, timescale):
    """Convert ticks to seconds."""
    return ticks / timescale


def convert_sec_to_ticks(seconds, timescale):
    """Convert seconds to ticks."""
    return seconds * timescale


def convert_sec_to_date(seconds, offset_hours=1):
    """Convert seconds to datetime with offset."""
    dt = datetime.datetime.utcfromtimestamp(seconds) + datetime.timedelta(hours=offset_hours)
    return dt


def convert_date_to_sec(dt, offset_hours=1):
    """Convert datetime to seconds with offset."""
    epoch = datetime.datetime(1970, 1, 1)
    utc_dt = dt - datetime.timedelta(hours=offset_hours)
    return (utc_dt - epoch).total_seconds()


def convert_date_to_ticks(dt, timescale, offset_hours=1):
    """Convert datetime to ticks with offset."""
    return int(round(convert_date_to_sec(dt, offset_hours) * timescale))


def past(rep, base, duration):
    """Calculate past tick."""
    return base - rep * duration


def future(rep, base, duration):
    """Calculate future tick."""
    return base + rep * duration


async def bruteforce(track_id, date):
    """Bruteforce segments to find valid ticks."""
    valid_ticks = []

    total_requests = 288000
    pas = 20000

    for i in range(total_requests // pas):
        debut = pas * i
        fin = debut + pas

        segment_num = i + 1
        total_segments = total_requests // pas
        print(f"\n🚀 Starting bruteforce segment {segment_num}/{total_segments} "
              f"(ticks {debut} to {fin})...")

        checked_ticks = set()
        ticks_to_check = list(range(debut, fin))
        start_time = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                tasks = [fetch_segment(session, t+date, track_id) for t in ticks_to_check]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                new_valid = [r for r in results if r and not isinstance(r, Exception)]
                valid_ticks.extend(new_valid)

                # Mark all checked ticks
                checked_ticks.update(ticks_to_check)
        except KeyboardInterrupt:
            print("\n\n🛑 Interrupted by user (Ctrl+C)")
            # Save progress even if interrupted
            checked_ticks.update(list(ticks_to_check))  # Mark attempted as checked
            end_time = time.time()
            elapsed = end_time - start_time
            req_per_sec = len(ticks_to_check) / elapsed if elapsed > 0 else 0

            print(f"\n{'='*50}")
            print(f"✅ Completed in {elapsed:.2f}s")
            print(f"⚡ Speed: {req_per_sec:.2f} req/s")
            print(f"📊 Total checked: {len(checked_ticks)}/{total_requests}")
            print(f"🎯 Valid ticks found: {len(valid_ticks)}")
            # print(f"💾 Progress saved to {PROGRESS_FILE}")
            print(f"{'='*50}")
        if valid_ticks:
            checked_ticks.update(list(ticks_to_check))
            end_time = time.time()
            elapsed = end_time - start_time
            req_per_sec = len(ticks_to_check) / elapsed if elapsed > 0 else 0
            print(f"✅ Completed in {elapsed:.2f}s")
            print(f"⚡ Speed: {req_per_sec:.2f} req/s")
            print(f"📊 Total checked: {len(checked_ticks)}/{total_requests}")
            print("Ticks valides :", valid_ticks)
            # break from the for loop if valid ticks found
            break


def find_nearest_tick_by_hour(base_tick, datetime_str, timescale, duration, offset_hours=1):
    """Find the nearest tick for a given datetime."""
    dt = datetime.datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
    target_ticks = convert_date_to_ticks(dt, timescale, offset_hours)
    diff_ticks = base_tick - target_ticks
    rep_estimate = diff_ticks / duration

    # Determine if we need to go to past or future
    if rep_estimate < 0:
        # Target is in the future from base
        rep = int(round(abs(rep_estimate)))
        nearest_tick = base_tick + rep * duration
    else:
        # Target is in the past from base
        rep = int(round(rep_estimate))
        nearest_tick = base_tick - rep * duration

    nearest_seconds = convert_ticks_to_sec(nearest_tick, timescale)
    target_seconds = convert_ticks_to_sec(target_ticks, timescale)
    delta_seconds = abs(nearest_seconds - target_seconds)

    print(f"Requested datetime: {dt} (offset +{offset_hours}h)")
    print(f"Nearest rep: {rep}")
    print(f"Tick: {nearest_tick}")
    print(f"Date: {convert_sec_to_date(nearest_seconds, offset_hours)}")
    print(f"Difference: {delta_seconds:.2f} seconds")

    return nearest_tick, rep
