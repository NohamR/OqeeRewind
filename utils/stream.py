"""Utility module for streaming and manifest parsing."""
import xml.etree.ElementTree as ET
import base64
import os
import asyncio
import time
from typing import Dict, Any
from uuid import UUID

import requests
from dotenv import load_dotenv
import aiohttp
from pywidevine.pssh import PSSH

load_dotenv()


def fetch_drm_keys(kid: str) -> str:
    """Fetch DRM keys for a given KID.

    Args:
        kid: The key identifier string.

    Returns:
        The DRM key as a string.
    """
    headers = {
        'Content-Type': 'application/json',
        'Api-Key': os.getenv("API_KEY"),
    }
    data = {"service": "oqee", "kid": kid}
    response = requests.post(
        os.getenv("API_URL"), headers=headers, json=data, timeout=10
    )
    return response.json()["key"]


def generate_pssh(kid: str) -> str:
    """Generate a PSSH box for a given KID.

    Args:
        kid: The key identifier string.
    
    Returns:
        The PSSH box as a base64-encoded string.
    """
    default_pssh = (
        "AAAAiHBzc2gAAAAA7e+LqXnWSs6jyCfc1R0h7QAAAGgIARIQrKzUjhLvvbqkebbW2/EQtBIQ"
        "WxKIsxtqP3iaIFYUu9f6xxIQXn4atxoopds39jbUXbiFVBIQUUJpv9uuzWKv4ccKTtooMRIQ"
        "ocf9FUFCoGm775zPIBr3HRoAKgAyADgASABQAA=="
    )
    pssh = PSSH(default_pssh)
    pssh.set_key_ids([UUID(kid.replace("-", "").lower())])
    return pssh.dumps()


def parse_mpd_manifest(mpd_content: str) -> Dict[str, Any]:
    """Parse an MPD manifest and extract metadata.

    Args:
        mpd_content: The MPD manifest content as a string.

    Returns:
        A dictionary containing parsed manifest information.
    """
    root = ET.fromstring(mpd_content)
    namespaces = {
        'mpd': 'urn:mpeg:dash:schema:mpd:2011',
        'cenc': 'urn:mpeg:cenc:2013'
    }

    manifest_info = {
        'type': root.get('type'),
        'profiles': root.get('profiles'),
        'publishTime': root.get('publishTime'),
        'availabilityStartTime': root.get('availabilityStartTime'),
        'minimumUpdatePeriod': root.get('minimumUpdatePeriod'),
        'minBufferTime': root.get('minBufferTime'),
        'timeShiftBufferDepth': root.get('timeShiftBufferDepth'),
        'suggestedPresentationDelay': root.get('suggestedPresentationDelay'),
        'periods': []
    }

    for period in root.findall('mpd:Period', namespaces):
        period_info = {
            'id': period.get('id'),
            'start': period.get('start'),
            'adaptation_sets': []
        }
        for adaptation_set in period.findall('mpd:AdaptationSet', namespaces):
            adaptation_info = parse_adaptation_set(adaptation_set, namespaces)
            period_info['adaptation_sets'].append(adaptation_info)
        manifest_info['periods'].append(period_info)
    return manifest_info


def parse_adaptation_set(
    adaptation_set: ET.Element, namespaces: Dict[str, str]
) -> Dict[str, Any]:
    """Parse an AdaptationSet element from MPD manifest.

    Args:
        adaptation_set: The AdaptationSet XML element.
        namespaces: XML namespaces dictionary.

    Returns:
        A dictionary containing parsed adaptation set information.
    """
    adaptation_info = {
        'id': adaptation_set.get('id'),
        'group': adaptation_set.get('group'),
        'contentType': adaptation_set.get('contentType'),
        'lang': adaptation_set.get('lang'),
        'segmentAlignment': adaptation_set.get('segmentAlignment'),
        'startWithSAP': adaptation_set.get('startWithSAP'),
        'drm_info': [],
        'representations': []
    }

    # Parse ContentProtection
    for content_protection in adaptation_set.findall(
        'mpd:ContentProtection', namespaces
    ):
        drm_info = parse_content_protection(content_protection, namespaces)
        adaptation_info['drm_info'].append(drm_info)

    # Parse Role
    role = adaptation_set.find('mpd:Role', namespaces)
    if role is not None:
        adaptation_info['role'] = role.get('value')

    # Parse Representations
    for representation in adaptation_set.findall('mpd:Representation', namespaces):
        rep_info = parse_representation(representation, namespaces)
        adaptation_info['representations'].append(rep_info)

    return adaptation_info


def parse_content_protection(
    content_protection: ET.Element, namespaces: Dict[str, str]
) -> Dict[str, Any]:
    """Parse ContentProtection element for DRM information.

    Args:
        content_protection: The ContentProtection XML element.
        namespaces: XML namespaces dictionary.

    Returns:
        A dictionary containing DRM information.
    """
    drm_info = {
        'schemeIdUri': content_protection.get('schemeIdUri'),
        'value': content_protection.get('value')
    }

    default_kid = content_protection.get('{urn:mpeg:cenc:2013}default_KID')
    if default_kid:
        drm_info['default_KID'] = default_kid

    pssh_element = content_protection.find('cenc:pssh', namespaces)
    if pssh_element is not None and pssh_element.text:
        drm_info['pssh'] = pssh_element.text.strip()
        try:
            pssh_decoded = base64.b64decode(drm_info['pssh'])
            drm_info['pssh_hex'] = pssh_decoded.hex()
        except (ValueError, base64.binascii.Error):
            pass

    return drm_info


def parse_representation(
    representation: ET.Element, namespaces: Dict[str, str]
) -> Dict[str, Any]:
    """Parse Representation element from MPD manifest.

    Args:
        representation: The Representation XML element.
        namespaces: XML namespaces dictionary.

    Returns:
        A dictionary containing parsed representation information.
    """
    rep_info = {
        'id': representation.get('id'),
        'bandwidth': representation.get('bandwidth'),
        'codecs': representation.get('codecs'),
        'mimeType': representation.get('mimeType'),
        'width': representation.get('width'),
        'height': representation.get('height'),
        'frameRate': representation.get('frameRate'),
        'segments': {}
    }

    segment_template = representation.find('mpd:SegmentTemplate', namespaces)
    if segment_template is not None:
        rep_info['segments'] = {
            'timescale': segment_template.get('timescale'),
            'initialization': segment_template.get('initialization'),
            'media': segment_template.get('media'),
            'timeline': []
        }

        segment_timeline = segment_template.find('mpd:SegmentTimeline', namespaces)
        if segment_timeline is not None:
            for s_element in segment_timeline.findall('mpd:S', namespaces):
                timeline_info = {
                    't': s_element.get('t'),  # start time
                    'd': s_element.get('d'),  # duration
                    'r': s_element.get('r')   # repeat count
                }
                rep_info['segments']['timeline'].append(timeline_info)

    return rep_info


# pylint: disable=too-many-locals,too-many-branches
def organize_by_content_type(manifest_info: Dict[str, Any]) -> Dict[str, Any]:
    """Organize manifest information by content type.

    Args:
        manifest_info: Parsed manifest information dictionary.

    Returns:
        A dictionary organized by content type (video, audio, text).
    """
    organized = {
        'video': {},
        'audio': {},
        'text': {},
        'manifest_metadata': {
            'type': manifest_info.get('type'),
            'publishTime': manifest_info.get('publishTime'),
            'minBufferTime': manifest_info.get('minBufferTime'),
        }
    }

    for period in manifest_info.get('periods', []):
        for adaptation_set in period.get('adaptation_sets', []):
            content_type = adaptation_set.get('contentType')

            if not content_type:
                continue

            for rep in adaptation_set.get('representations', []):
                track_info = {
                    'track_id': rep.get('id'),
                    'adaptation_set_id': adaptation_set.get('id'),
                    'bandwidth': int(rep.get('bandwidth', 0)),
                    'bitrate_kbps': int(rep.get('bandwidth', 0)) // 1000,
                    'codec': rep.get('codecs'),
                    'mime_type': rep.get('mimeType'),
                    'drm_info': adaptation_set.get('drm_info', []),
                    'segments': rep.get('segments', {}),
                }

                if content_type == 'video':
                    width = rep.get('width')
                    height = rep.get('height')
                    frame_rate = rep.get('frameRate')

                    track_info.update({
                        'resolution': (
                            f"{width}x{height}" if width and height else 'unknown'
                        ),
                        'width': int(width) if width else None,
                        'height': int(height) if height else None,
                        'frame_rate': frame_rate,
                    })

                    resolution_key = track_info['resolution']
                    if resolution_key not in organized['video']:
                        organized['video'][resolution_key] = []
                    organized['video'][resolution_key].append(track_info)

                elif content_type == 'audio':
                    lang = adaptation_set.get('lang', 'unknown')
                    role = adaptation_set.get('role', 'main')

                    track_info.update({
                        'language': lang,
                        'role': role,
                    })

                    lang_key = f"{lang}_{role}"
                    if lang_key not in organized['audio']:
                        organized['audio'][lang_key] = []
                    organized['audio'][lang_key].append(track_info)

                elif content_type == 'text':
                    lang = adaptation_set.get('lang', 'unknown')
                    role = adaptation_set.get('role', 'caption')

                    track_info.update({
                        'language': lang,
                        'role': role,
                    })

                    lang_key = f"{lang}_{role}"
                    if lang_key not in organized['text']:
                        organized['text'][lang_key] = []
                    organized['text'][lang_key].append(track_info)

    # Sort video tracks by resolution (descending) and then by bitrate (descending)
    for resolution in organized['video']:
        organized['video'][resolution].sort(
            key=lambda x: x['bandwidth'], reverse=True
        )

    # Sort audio tracks by bitrate (descending)
    for lang in organized['audio']:
        organized['audio'][lang].sort(key=lambda x: x['bandwidth'], reverse=True)

    # Sort video resolutions by pixel count (descending)
    sorted_video = {}
    for resolution in sorted(
        organized['video'].keys(),
        key=lambda r: (
            int(r.split('x')[0]) * int(r.split('x')[1])
            if 'x' in r and r.split('x')[0].isdigit() else 0
        ),
        reverse=True
    ):
        sorted_video[resolution] = organized['video'][resolution]
    organized['video'] = sorted_video

    return organized


def get_manifest(manifest_id):
    """Fetch the MPD manifest for a given channel ID.

    Args:
        manifest_id: The channel/manifest identifier.

    Returns:
        The manifest content as text.
    """
    headers = {
        'accept': '*/*',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'cache-control': 'no-cache',
        'origin': 'https://tv.free.fr',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://tv.free.fr/',
        'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
    }

    format_id = 1
    url = (
        f'https://api-proxad.dc2.oqee.net/playlist/v1/live/'
        f'{manifest_id}/{format_id}/live.mpd'
    )
    response = requests.get(url, headers=headers, timeout=10)
    return response.text


async def fetch_segment(session, ticks, track_id):
    """Fetch a media segment asynchronously.

    Args:
        session: The aiohttp ClientSession.
        ticks: The tick value for the segment.
        track_id: The track identifier.

    Returns:
        The tick value if successful, None otherwise.
    """
    url = f"https://media.stream.proxad.net/media/{track_id}_{ticks}"
    headers = {
        'Accept': '*/*',
        'Referer': 'https://tv.free.fr/',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
    }
    try:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                return ticks
            return None
    except aiohttp.ClientError:
        return None

def get_init(track_id):
    """Download and save the initialization segment for a track.

    Args:
        track_id: The track identifier.
    """
    url = f"https://media.stream.proxad.net/media/{track_id}_init"
    headers = {
        'Accept': '*/*',
        'Referer': 'https://tv.free.fr/',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
    }
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 200:
        with open(f'segments/segments_{track_id}/init.mp4', 'wb') as f:
            f.write(response.content)
        print(f"✅ Saved initialization segment to init_{track_id}.mp4")


async def save_segments(track_id, start_tick, rep_nb, duration):
    """Download and save multiple media segments.

    Args:
        track_id: The track identifier.
        start_tick: The starting tick value.
        rep_nb: The number of segments to download.
        duration: The duration per segment.
    """
    os.makedirs(f'segments/segments_{track_id}', exist_ok=True)

    async def download_segment(session, tick, rep):
        """Download a single segment."""
        url = f"https://media.stream.proxad.net/media/{track_id}_{tick}"
        headers = {
            'Accept': '*/*',
            'Referer': 'https://tv.free.fr/',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        }
        try:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    content = await resp.read()
                    filename = f"segments/segments_{track_id}/{tick}.m4s"
                    with open(filename, 'wb') as f:
                        f.write(content)
                    print(
                        f"✅ Saved segment {rep} (tick {tick}) to {filename}"
                    )
                    return True
                print(
                    f"❌ Failed to download segment {rep} (tick {tick}): "
                    f"HTTP {resp.status}"
                )
                return False
        except aiohttp.ClientError as e:
            print(f"⚠️ Error downloading segment {rep} (tick {tick}): {e}")
            return False

    print(f"\n🎬 Starting download of {rep_nb} segments...")
    print(f"📦 Track ID: {track_id}")
    print(f"🎯 Base tick: {start_tick}")
    print(f"{'='*50}\n")

    start_time = time.time()
    successful = 0
    failed = 0

    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(rep_nb):
            tick = start_tick + i * duration
            tasks.append(download_segment(session, tick, i))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful = sum(1 for r in results if r is True)
        failed = rep_nb - successful

    end_time = time.time()
    elapsed = end_time - start_time

    print(f"\n{'='*50}")
    print(f"✅ Download completed in {elapsed:.2f}s")
    print(f"📊 Successful: {successful}/{rep_nb}")
    print(f"❌ Failed: {failed}/{rep_nb}")
    print(f"💾 Files saved to segments_{track_id}/")
    print(f"{'='*50}")


def get_kid(track_id):
    """Extract the Key ID (KID) from downloaded segments.

    Args:
        track_id: The track identifier.

    Returns:
        The KID as a hex string if found, None otherwise.
    """
    folder = f'segments/segments_{track_id}'
    for filename in os.listdir(folder):
        if filename.endswith('.m4s'):
            filepath = os.path.join(folder, filename)
            print(f"Checking file: {filepath}")
            with open(filepath, 'rb') as f:
                data = f.read()
                # Pattern before KID
                index = data.find(
                    b'\x73\x65\x69\x67\x00\x00\x00\x14'
                    b'\x00\x00\x00\x01\x00\x00\x01\x10'
                )
                if index != -1:
                    kid_bytes = data[index + 16:index + 16 + 16]
                    kid = kid_bytes.hex()
                    return kid
    return None
