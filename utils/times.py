"""Utility functions for time and tick conversions, and bruteforce operations."""

import asyncio
import datetime
import time

import aiohttp
from tqdm import tqdm

from utils.stream import fetch_segment
from utils.logging_config import logger


def convert_ticks_to_sec(ticks, timescale):
    """Convert ticks to seconds."""
    return ticks / timescale


def convert_sec_to_ticks(seconds, timescale):
    """Convert seconds to ticks."""
    return seconds * timescale


def convert_sec_to_date(seconds, offset_hours=1):
    """Convert seconds to datetime with offset."""
    dt = datetime.datetime.utcfromtimestamp(seconds) + datetime.timedelta(
        hours=offset_hours
    )
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
    batch_size = 20000

    logger.debug("Starting bruteforce for %s near %s", track_id, date)

    start_time = time.time()

    try:
        async with aiohttp.ClientSession() as session:
            for batch_start in range(0, total_requests, batch_size):
                batch_end = min(batch_start + batch_size, total_requests)
                tasks = [
                    fetch_segment(session, t + date, track_id)
                    for t in range(batch_start, batch_end)
                ]

                results = []
                for coro in tqdm(
                    asyncio.as_completed(tasks),
                    total=len(tasks),
                    desc="Bruteforce",
                    unit="req",
                ):
                    result = await coro
                    results.append(result)

                valid_ticks.extend(
                    [r for r in results if r and not isinstance(r, Exception)]
                )

                # Stop if we found valid ticks
                if valid_ticks:
                    logger.debug("Found valid ticks: %s, stopping bruteforce.", valid_ticks)
                    break

    except KeyboardInterrupt:
        logger.error("Interrupted by user (Ctrl+C)")

    elapsed = time.time() - start_time
    logger.debug("Completed in %.2fs", elapsed)
    logger.debug("Speed: %.2f req/s", total_requests / elapsed if elapsed > 0 else 0)
    logger.debug("Total checked: %d", total_requests)

    return valid_ticks


def find_nearest_tick_by_hour(base_tick, dt, timescale, duration, offset_hours=1):
    """Find the nearest tick for a given datetime."""
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

    # print(f"Requested datetime: {dt} (offset +{offset_hours}h)")
    # print(f"Nearest rep: {rep}")
    # print(f"Tick: {nearest_tick}")

    return nearest_tick, rep
