"""Input utilities for user prompts and channel/stream selection."""

import datetime
import requests
from prompt_toolkit.validation import Validator, ValidationError
from InquirerPy import prompt
from InquirerPy.validator import EmptyInputValidator
from InquirerPy.base.control import Choice

from utils.stream import get_manifest, parse_mpd_manifest, organize_by_content_type
from utils.logging_config import logger

SERVICE_PLAN_API_URL = "https://api.oqee.net/api/v6/service_plan"
EPG_API_URL = "https://api.oqee.net/api/v1/epg/all/{unix}"


class DatetimeValidator(Validator):
    """
    Custom validator for datetime strings in "YYYY-MM-DD HH:MM:SS" format.
    """

    def validate(self, document):
        try:
            datetime.datetime.strptime(document.text, "%Y-%m-%d %H:%M:%S")
        except ValueError as exc:
            raise ValidationError(
                message="Please enter a valid date/time in YYYY-MM-DD HH:MM:SS format",
                cursor_position=len(document.text),
            ) from exc


class DurationValidator(Validator):
    """
    Custom validator for duration strings in "HH:MM:SS" format.
    """

    def validate(self, document):
        parts = document.text.split(":")
        if len(parts) != 3:
            raise ValidationError(
                message="Please enter the duration in HH:MM:SS format",
                cursor_position=len(document.text),
            )
        try:
            _, m, s = [int(part) for part in parts]
            if not (0 <= m < 60 and 0 <= s < 60):
                raise ValueError(
                    "Minutes and seconds must be between 0 and 59."
                )
        except ValueError as exc:
            raise ValidationError(
                message="Invalid format. Use HH:MM:SS with valid numbers.",
                cursor_position=len(document.text),
            ) from exc


def get_date_input():
    """Prompt user for start and end date/time or duration.

    Returns:
        tuple: A tuple containing (start_date, end_date) as datetime objects.
    """
    question_start_date = [
        {
            "type": "input",
            "message": "Enter a start date/time (YYYY-MM-DD HH:MM:SS):",
            "name": "datetime",
            "default": "2025-01-01 12:00:00",
            "validate": DatetimeValidator(),
            "invalid_message": "Invalid date/time format. Use YYYY-MM-DD HH:MM:SS",
        }
    ]

    start_date_result = prompt(question_start_date)
    if start_date_result:
        start_date = datetime.datetime.strptime(
            start_date_result["datetime"], "%Y-%m-%d %H:%M:%S"
        )
        logger.debug("Start date/time: %s", start_date)

    question_end_date = [
        {
            "type": "list",
            "message": "What would you like to enter?",
            "choices": ["Duration", "End date/time"],
            "name": "input_type",
        },
        {
            "type": "input",
            "message": "Enter the duration (HH:MM:SS):",
            "name": "duration",
            "default": "01:00:00",
            "validate": DurationValidator(),
            "when": lambda answers: answers["input_type"] == "Duration",
        },
        {
            "type": "input",
            "message": "Enter an end date/time (YYYY-MM-DD HH:MM:SS):",
            "name": "datetime",
            "default": (
                start_date_result["datetime"]
                if start_date_result
                else "2025-01-01 12:00:00"
            ),
            "validate": DatetimeValidator(),
            "when": lambda answers: answers["input_type"] == "End date/time",
        },
    ]

    end_date_result = prompt(question_end_date)

    if end_date_result:
        if end_date_result.get("duration"):
            duration_str = end_date_result["duration"]
            try:
                h, m, s = map(int, duration_str.split(":"))
                duration_td = datetime.timedelta(hours=h, minutes=m, seconds=s)
                end_date = start_date + duration_td
                logger.debug("End date/time: %s", end_date)
            except (ValueError, TypeError):
                logger.error("Unable to parse the provided duration string.")

        elif end_date_result.get("datetime"):
            try:
                end_date = datetime.datetime.strptime(
                    end_date_result["datetime"], "%Y-%m-%d %H:%M:%S"
                )
                logger.debug("End date/time: %s", end_date)
            except (ValueError, TypeError):
                logger.error("Unable to parse the provided date/time string.")
    return start_date, end_date


def select_oqee_channel():
    """Select an Oqee channel from the API.

    Returns:
        dict: Selected channel details or None if cancelled/error.
    """
    api_url = SERVICE_PLAN_API_URL
    try:
        logger.info("Loading channel list from Oqee API...")
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if not data.get("success") or "channels" not in data.get("result", {}):
            logger.error("Error: Unexpected API response format.")
            return None

        channels_data = data["result"]["channels"]
        choices = [
            {"name": f"{channel_info.get('name', 'Unknown name')}", "value": channel_id}
            for channel_id, channel_info in channels_data.items()
        ]
        choices.sort(key=lambda x: x["name"])

    except requests.exceptions.RequestException as e:
        logger.error("A network error occurred: %s", e)
        return None
    except ValueError:
        logger.error("Error parsing JSON response.")
        return None

    questions = [
        {
            "type": "fuzzy",
            "message": "Please choose a channel (type to filter):",
            "choices": choices,
            "multiselect": False,
            "validate": EmptyInputValidator(),
            "invalid_message": "You must select a channel.",
            "long_instruction": "Use arrows to navigate, Enter to select.",
        }
    ]

    try:
        result = prompt(questions)
        selected_channel_id = result[0]
        selected_channel_details = channels_data.get(selected_channel_id)
        if selected_channel_details:
            logger.info("You have selected:")
            logger.info("  Name: %s", selected_channel_details.get("name"))
            logger.info("  ID: %s", selected_channel_details.get("id"))
            logger.info("  Freebox ID: %s", selected_channel_details.get("freebox_id"))
        else:
            logger.warning("Unable to find details for the selected channel.")
        return selected_channel_details

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user.")
        return None
    except (ValueError, KeyError, IndexError) as e:
        logger.error("An unexpected error occurred: %s", e)
        return None


def prompt_for_stream_selection(stream_info, already_selected_types):
    """Guide the user to select a stream, disabling already chosen types."""
    try:
        content_type_choices = [
            Choice(value, name=value, enabled=value not in already_selected_types)
            for value in stream_info.keys()
        ]

        questions = [
            {
                "type": "list",
                "message": "Which stream type would you like to select?",
                "choices": content_type_choices,
            }
        ]
        result = prompt(questions)
        if not result:
            return None
        selected_type = result[0]

        selected_content_data = stream_info[selected_type]

        questions = [
            {
                "type": "list",
                "message": f"Choose a quality for '{selected_type}':",
                "choices": list(selected_content_data.keys()),
            }
        ]
        result = prompt(questions)
        if not result:
            return None
        quality_group_key = result[0]

        available_streams = selected_content_data[quality_group_key]

        final_selection = None
        if len(available_streams) == 1:
            final_selection = available_streams[0]
            logger.debug("Only one stream available for this quality, automatic selection.")
        else:
            stream_choices = [
                {
                    "name": (
                        f"Bitrate: {s.get('bitrate_kbps')} kbps | "
                        f"Codec: {s.get('codec', 'N/A')} | ID: {s.get('track_id')}"
                    ),
                    "value": s,
                }
                for s in available_streams
            ]
            questions = [
                {
                    "type": "list",
                    "message": "Multiple streams are available, please choose one:",
                    "choices": stream_choices,
                }
            ]
            result = prompt(questions)
            if not result:
                return None
            final_selection = result[0]

        final_selection["content_type"] = selected_type
        return final_selection

    except (KeyboardInterrupt, TypeError):
        return None


def stream_selection():
    """Guide user through channel and stream selection process.

    Returns:
        dict: Dictionary of selected streams by content type, or None if cancelled.
    """
    selected_channel = select_oqee_channel()

    if not selected_channel:
        return None

    logger.debug("Selected channel:")
    logger.debug("  - Name: %s", selected_channel.get("name"))
    logger.debug("  - ID: %s", selected_channel.get("id"))

    dash_id = selected_channel.get("streams", {}).get("dash")
    if not dash_id:
        logger.error("No DASH stream found for this channel.")
        return None

    mpd_content = get_manifest(dash_id)
    manifest_info = parse_mpd_manifest(mpd_content)
    organized_info = organize_by_content_type(manifest_info)

    final_selections = {}

    while True:
        selection = prompt_for_stream_selection(organized_info, final_selections.keys())

        if selection:
            content_type = selection.pop("content_type")
            final_selections[content_type] = selection

            logger.info("--- Selection Summary ---")
            for stream_type, details in final_selections.items():
                bitrate = details.get("bitrate_kbps")
                track_id = details.get("track_id")
                logger.info(
                    "  - %s: Bitrate %s kbps (ID: %s)",
                    stream_type.capitalize(), bitrate, track_id
                )
            logger.info("----------------------------------------")

        continue_prompt = [
            {
                "type": "list",
                "message": "What would you like to do?",
                "choices": ["Select another stream", "Finish and continue"],
            }
        ]
        action_result = prompt(continue_prompt)

        if not action_result or action_result[0] == "Finish and continue":
            break

    if final_selections:
        final_selections["channel"] = selected_channel
        return final_selections

    logger.info("No stream has been selected.")
    return None


def get_selection(channel_id, video_quality="best", audio_quality="best"):
    """Get stream selection for a given channel ID with specified qualities.

    Args:
        channel_id (str): The channel ID to select streams for.
        video_quality (str): Video quality selection ('best', '1080+best', '720+worst', etc.).
        audio_quality (str): Audio quality selection ('best', 'fra+best', etc.).

    Returns:
        dict: Dictionary of selected streams by content type, or None if error.
    """
    # Fetch channel details
    api_url = SERVICE_PLAN_API_URL
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if not data.get("success") or "channels" not in data.get("result", {}):
            logger.error("Error: Unable to retrieve channel details.")
            return None

        channels_data = data["result"]["channels"]
        selected_channel_details = channels_data.get(str(channel_id))
        if not selected_channel_details:
            logger.error("Channel with ID %s not found.", channel_id)
            return None

    except requests.exceptions.RequestException as e:
        logger.error("Network error: %s", e)
        return None
    except ValueError:
        logger.error("Error parsing JSON response.")
        return None

    logger.info(
        "Selected channel: %s (ID: %s)",
        selected_channel_details.get("name"), channel_id
    )

    dash_id = selected_channel_details.get("streams", {}).get("dash")
    if not dash_id:
        logger.error("No DASH stream found for this channel.")
        return None

    mpd_content = get_manifest(dash_id)
    manifest_info = parse_mpd_manifest(mpd_content)
    organized_info = organize_by_content_type(manifest_info)

    final_selections = {}
    final_selections["channel"] = selected_channel_details

    # Select video
    if "video" in organized_info:
        selected_track = select_track(organized_info["video"], video_quality, "video")
        if selected_track:
            final_selections["video"] = selected_track

    # Select audio
    if "audio" in organized_info:
        selected_track = select_track(organized_info["audio"], audio_quality, "audio")
        if selected_track:
            final_selections["audio"] = selected_track

    return final_selections


def select_track(content_dict, quality_spec, content_type):
    """Select a track based on quality specification.

    Args:
        content_dict (dict): Organized content dict (video or audio).
        quality_spec (str): Quality spec like 'best', '1080+best', 'fra+worst'.
        content_type (str): 'video' or 'audio'.

    Returns:
        dict: Selected track or None.
    """
    if quality_spec is None:
        logger.error(
            f"No {content_type} quality specified. Use --{content_type} option "
            f"(e.g., --{content_type} best)"
        )
        return None

    if "+" in quality_spec:
        filter_part, pref = quality_spec.split("+", 1)
        pref = pref.lower()
    else:
        filter_part = ""
        pref = quality_spec.lower()

    candidates = []
    for key, tracks in content_dict.items():
        if filter_part:
            should_skip = True
            if content_type == "video" and "x" in key:
                # For video, check height
                try:
                    _, height = key.split("x")
                    if filter_part.endswith("p"):
                        target_height = filter_part[:-1]
                    else:
                        target_height = filter_part
                    if target_height in height:
                        should_skip = False
                except ValueError:
                    pass
            if should_skip and filter_part.lower() not in key.lower():
                continue
        candidates.extend(tracks)

    if not candidates:
        logger.warning("No %s track found for '%s'.", content_type, quality_spec)
        return None

    if pref == "best":
        selected = max(candidates, key=lambda x: x["bandwidth"])
    elif pref == "worst":
        selected = min(candidates, key=lambda x: x["bandwidth"])
    else:
        # Default to best if unknown pref
        selected = max(candidates, key=lambda x: x["bandwidth"])

    logger.info(
        "%s selected: %s, %d kbps",
        content_type.capitalize(), selected["track_id"], selected["bitrate_kbps"]
    )
    return selected


def get_epg_data_at(dt: datetime.datetime):
    """
    Fetch EPG data from the Oqee API for the nearest aligned hour of a given datetime.

    Args:
        dt (datetime.datetime): datetime (with hour, minute, etc.)

    Returns:
        dict | None: EPG data or None on error
    """

    # Round to nearest hour
    if dt.minute >= 30:
        dt_aligned = (dt + datetime.timedelta(hours=1)).replace(
            minute=0, second=0, microsecond=0
        )
    else:
        dt_aligned = dt.replace(minute=0, second=0, microsecond=0)

    unix_time = int(dt_aligned.timestamp())
    logger.info("Fetching EPG for aligned time: %s (unix=%d)", dt_aligned, unix_time)

    try:
        response = requests.get(EPG_API_URL.format(unix=unix_time), timeout=10)
        response.raise_for_status()
        data = response.json()

        return data.get("result")

    except requests.exceptions.RequestException as e:
        logger.error("A network error occurred: %s", e)
        return None
    except ValueError:
        logger.error("Error parsing JSON response.")
        return None


def select_program_from_epg(programs, original_start_date, original_end_date):
    """
    Prompt user to select a program from EPG data or keep original selection.

    Args:
        programs (list): List of program dictionaries from EPG data
        original_start_date (datetime.datetime): User's original start date selection
        original_end_date (datetime.datetime): User's original end date selection

    Returns:
        dict: Dictionary containing:
            - 'start_date': datetime object for start
            - 'end_date': datetime object for end
            - 'title': str or None (program title if selected)
            - 'program': dict or None (full program data if selected)
    """
    if not programs:
        logger.warning("No programs available in the EPG guide.")
        return {
            "start_date": original_start_date,
            "end_date": original_end_date,
            "title": None,
            "program": None,
        }

    # Create choices list with program information
    program_choices = []
    for program in programs:
        # Extract the live data from the program
        live_data = program.get("live", program)
        title = live_data.get("title", "Untitled")
        start_time = datetime.datetime.fromtimestamp(live_data.get("start", 0))
        end_time = datetime.datetime.fromtimestamp(live_data.get("end", 0))
        duration_min = (end_time - start_time).total_seconds() / 60

        choice_name = (
            f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')} | "
            f"{title} ({int(duration_min)} min)"
        )
        program_choices.append(
            {"name": choice_name, "value": program}  # Store the full program object
        )

    # Add option to keep original selection
    program_choices.insert(
        0,
        {
            "name": (
                f"Keep original manual selection "
                f"({original_start_date.strftime('%Y-%m-%d %H:%M:%S')} - "
                f"{original_end_date.strftime('%Y-%m-%d %H:%M:%S')})"
            ),
            "value": None,
        },
    )

    questions = [
        {
            "type": "list",
            "message": "Select a program or keep your manual selection:",
            "choices": program_choices,
            "long_instruction": "Use arrows to navigate, Enter to select.",
        }
    ]

    try:
        result = prompt(questions)
        if not result:
            return None

        selected_program = result[0]

        # If user chose to keep original selection
        if selected_program is None:
            logger.info("Manual selection kept")
            return {
                "start_date": original_start_date,
                "end_date": original_end_date,
                "title": None,
                "program": None,
            }

        # Extract live data and convert program timestamps to datetime objects
        live_data = selected_program.get("live", selected_program)
        program_start = datetime.datetime.fromtimestamp(live_data.get("start", 0))
        program_end = datetime.datetime.fromtimestamp(live_data.get("end", 0))
        program_title = live_data.get("title", "Untitled")

        logger.info("Selected program:")
        logger.info("  - Title: %s", program_title)
        logger.info("  - Start: %s", program_start.strftime("%Y-%m-%d %H:%M:%S"))
        logger.info("  - End: %s", program_end.strftime("%Y-%m-%d %H:%M:%S"))

        return {
            "start_date": program_start,
            "end_date": program_end,
            "title": program_title,
            "program": selected_program,
        }

    except KeyboardInterrupt:
        logger.error("Operation cancelled by user.")
        return None
