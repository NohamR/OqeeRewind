"""Input utilities for user prompts and channel/stream selection."""
import datetime
import requests
from prompt_toolkit.validation import Validator, ValidationError
from InquirerPy import prompt
from InquirerPy.validator import EmptyInputValidator
from InquirerPy.base.control import Choice

from utils.stream import (
    get_manifest,
    parse_mpd_manifest,
    organize_by_content_type
)

SERVICE_PLAN_API_URL = "https://api.oqee.net/api/v6/service_plan"
EPG_API_URL = "https://api.oqee.net/api/v1/epg/all/{unix}"


class DatetimeValidator(Validator):
    """
    Validateur personnalisé pour les chaînes datetime au format "YYYY-MM-DD HH:MM:SS".
    """
    def validate(self, document):
        try:
            datetime.datetime.strptime(document.text, "%Y-%m-%d %H:%M:%S")
        except ValueError as exc:
            raise ValidationError(
                message="Veuillez entrer une date/heure valide au format YYYY-MM-DD HH:MM:SS",
                cursor_position=len(document.text),
            ) from exc


class DurationValidator(Validator):
    """
    Validateur personnalisé pour les chaînes de durée au format "HH:MM:SS".
    """
    def validate(self, document):
        parts = document.text.split(':')
        if len(parts) != 3:
            raise ValidationError(
                message="Veuillez entrer la durée au format HH:MM:SS",
                cursor_position=len(document.text),
            )
        try:
            _, m, s = [int(part) for part in parts]
            if not (0 <= m < 60 and 0 <= s < 60):
                raise ValueError("Les minutes et les secondes doivent être entre 0 et 59.")
        except ValueError as exc:
            raise ValidationError(
                message="Format invalide. Utilisez HH:MM:SS avec des nombres valides.",
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
            "message": "Entrez une date/heure de début (YYYY-MM-DD HH:MM:SS):",
            "name": "datetime",
            "default": "2025-01-01 12:00:00",
            "validate": DatetimeValidator(),
            "invalid_message": "Format de date/heure invalide. Utilisez YYYY-MM-DD HH:MM:SS",
        }
    ]

    start_date_result = prompt(question_start_date)
    if start_date_result:
        start_date = datetime.datetime.strptime(start_date_result["datetime"], "%Y-%m-%d %H:%M:%S")
        print(f"Date/heure de début : {start_date}")

    question_end_date = [
        {
            "type": "list",
            "message": "Que voulez-vous entrer ?",
            "choices": ["Durée", "Date/heure de fin"],
            "name": "input_type",
        },
        {
            "type": "input",
            "message": "Entrez la durée (HH:MM:SS):",
            "name": "duration",
            "default": "01:00:00",
            "validate": DurationValidator(),
            "when": lambda answers: answers["input_type"] == "Durée",
        },
        {
            "type": "input",
            "message": "Entrez une date/heure de fin (YYYY-MM-DD HH:MM:SS):",
            "name": "datetime",
            "default": (
                start_date_result["datetime"] if start_date_result
                else "2025-01-01 12:00:00"
            ),
            "validate": DatetimeValidator(),
            "when": lambda answers: answers["input_type"] == "Date/heure de fin",
        },
    ]

    end_date_result = prompt(question_end_date)

    if end_date_result:
        if end_date_result.get("duration"):
            duration_str = end_date_result["duration"]
            try:
                h, m, s = map(int, duration_str.split(':'))
                duration_td = datetime.timedelta(hours=h, minutes=m, seconds=s)
                end_date = start_date + duration_td
                print(f"\nDate/heure de fin : {end_date}")
            except (ValueError, TypeError):
                print("Impossible d'analyser la chaîne de durée fournie.")

        elif end_date_result.get("datetime"):
            try:
                end_date = datetime.datetime.strptime(
                    end_date_result["datetime"], "%Y-%m-%d %H:%M:%S"
                )
                print(f"\nDate/heure de fin : {end_date}")
            except (ValueError, TypeError):
                print("Impossible d'analyser la chaîne de date/heure fournie.")
    return start_date, end_date


def select_oqee_channel():
    """Select an Oqee channel from the API.

    Returns:
        dict: Selected channel details or None if cancelled/error.
    """
    api_url = SERVICE_PLAN_API_URL
    try:
        print("Chargement de la liste des chaînes depuis l'API Oqee...")
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if not data.get("success") or "channels" not in data.get("result", {}):
            print("Erreur: Le format de la réponse de l'API est inattendu.")
            return None

        channels_data = data["result"]["channels"]
        choices = [
            {
                "name": f"{channel_info.get('name', 'Nom inconnu')}",
                "value": channel_id
            }
            for channel_id, channel_info in channels_data.items()
        ]
        choices.sort(key=lambda x: x['name'])

    except requests.exceptions.RequestException as e:
        print(f"Une erreur réseau est survenue : {e}")
        return None
    except ValueError:
        print("Erreur lors de l'analyse de la réponse JSON.")
        return None

    questions = [
        {
            "type": "fuzzy",
            "message": "Veuillez choisir une chaîne (tapez pour filtrer) :",
            "choices": choices,
            "multiselect": False,
            "validate": EmptyInputValidator(),
            "invalid_message": "Vous devez sélectionner une chaîne.",
            "long_instruction": "Utilisez les flèches pour naviguer, Entrée pour sélectionner.",
        }
    ]

    try:
        result = prompt(questions)
        selected_channel_id = result[0]
        selected_channel_details = channels_data.get(selected_channel_id)
        if selected_channel_details:
            print("\n✅ Vous avez sélectionné :")
            print(f"  - Nom : {selected_channel_details.get('name')}")
            print(f"  - ID : {selected_channel_details.get('id')}")
            print(f"  - ID Freebox : {selected_channel_details.get('freebox_id')}")
        else:
            print("Impossible de retrouver les détails de la chaîne sélectionnée.")
        return selected_channel_details

    except KeyboardInterrupt:
        print("\nOpération annulée par l'utilisateur.")
        return None
    except (ValueError, KeyError, IndexError) as e:
        print(f"Une erreur inattenante est survenue : {e}")
        return None


def prompt_for_stream_selection(stream_info, already_selected_types):
    """Guide l'utilisateur pour sélectionner un flux, en désactivant les types déjà choisis."""
    try:
        content_type_choices = [
            Choice(value, name=value, enabled=value not in already_selected_types)
            for value in stream_info.keys()
        ]

        questions = [
            {
                "type": "list",
                "message": "Quel type de flux souhaitez-vous sélectionner ?",
                "choices": content_type_choices
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
                "message": f"Choisissez une qualité pour '{selected_type}':",
                "choices": list(selected_content_data.keys())
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
            print("Un seul flux disponible pour cette qualité, sélection automatique.")
        else:
            stream_choices = [
                {
                    "name": (
                        f"Bitrate: {s.get('bitrate_kbps')} kbps | "
                        f"Codec: {s.get('codec', 'N/A')} | ID: {s.get('track_id')}"
                    ),
                    "value": s
                }
                for s in available_streams
            ]
            questions = [
                {
                    "type": "list",
                    "message": "Plusieurs flux sont disponibles, choisissez-en un :",
                    "choices": stream_choices
                }
            ]
            result = prompt(questions)
            if not result:
                return None
            final_selection = result[0]

        final_selection['content_type'] = selected_type
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

    print("\n✅ Chaîne sélectionnée :")
    print(f"  - Nom : {selected_channel.get('name')}")
    print(f"  - ID : {selected_channel.get('id')}")

    dash_id = selected_channel.get('streams', {}).get('dash')
    if not dash_id:
        print("Aucun flux DASH trouvé pour cette chaîne.")
        return None

    mpd_content = get_manifest(dash_id)
    manifest_info = parse_mpd_manifest(mpd_content)
    organized_info = organize_by_content_type(manifest_info)

    final_selections = {}

    while True:
        selection = prompt_for_stream_selection(
            organized_info, final_selections.keys()
        )

        if selection:
            content_type = selection.pop('content_type')
            final_selections[content_type] = selection

            print("\n--- Récapitulatif de votre sélection ---")
            for stream_type, details in final_selections.items():
                bitrate = details.get('bitrate_kbps')
                track_id = details.get('track_id')
                print(
                    f"  - {stream_type.capitalize()}: "
                    f"Bitrate {bitrate} kbps (ID: {track_id})"
                )
            print("----------------------------------------")

        continue_prompt = [
            {
                "type": "list",
                "message": "Que souhaitez-vous faire ?",
                "choices": [
                    "Sélectionner un autre flux",
                    "Terminer et continuer"
                ],
            }
        ]
        action_result = prompt(continue_prompt)

        if (
            not action_result or
            action_result[0] == "Terminer et continuer"
        ):
            break

    if final_selections:
        final_selections['channel'] = selected_channel
        return final_selections

    print("\nAucun flux n'a été sélectionné.")
    return None


def get_selection(channel_id, video_quality='best', audio_quality='best'):
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
            print("Erreur: Impossible de récupérer les détails de la chaîne.")
            return None

        channels_data = data["result"]["channels"]
        selected_channel_details = channels_data.get(str(channel_id))
        if not selected_channel_details:
            print(f"Chaîne avec ID {channel_id} non trouvée.")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Erreur réseau : {e}")
        return None
    except ValueError:
        print("Erreur lors de l'analyse de la réponse JSON.")
        return None

    print(f"Chaîne sélectionnée : {selected_channel_details.get('name')} (ID: {channel_id})")

    dash_id = selected_channel_details.get('streams', {}).get('dash')
    if not dash_id:
        print("Aucun flux DASH trouvé pour cette chaîne.")
        return None

    mpd_content = get_manifest(dash_id)
    manifest_info = parse_mpd_manifest(mpd_content)
    organized_info = organize_by_content_type(manifest_info)

    final_selections = {}
    final_selections['channel'] = selected_channel_details

    # Select video
    if 'video' in organized_info:
        selected_track = select_track(organized_info['video'], video_quality, 'video')
        if selected_track:
            final_selections['video'] = selected_track

    # Select audio
    if 'audio' in organized_info:
        selected_track = select_track(organized_info['audio'], audio_quality, 'audio')
        if selected_track:
            final_selections['audio'] = selected_track

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
    if '+' in quality_spec:
        filter_part, pref = quality_spec.split('+', 1)
        pref = pref.lower()
    else:
        filter_part = ''
        pref = quality_spec.lower()

    candidates = []
    for key, tracks in content_dict.items():
        if filter_part and filter_part.lower() not in key.lower():
            continue
        candidates.extend(tracks)

    if not candidates:
        print(f"Aucune piste {content_type} trouvée pour '{quality_spec}'.")
        return None

    if pref == 'best':
        selected = max(candidates, key=lambda x: x['bandwidth'])
    elif pref == 'worst':
        selected = min(candidates, key=lambda x: x['bandwidth'])
    else:
        # Default to best if unknown pref
        selected = max(candidates, key=lambda x: x['bandwidth'])

    print(f"{content_type.capitalize()} sélectionnée : {selected['track_id']}, {selected['bitrate_kbps']} kbps")
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
        dt_aligned = (dt + datetime.timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    else:
        dt_aligned = dt.replace(minute=0, second=0, microsecond=0)

    unix_time = int(dt_aligned.timestamp())
    print(f"Fetching EPG for aligned time: {dt_aligned} (unix={unix_time})")

    try:
        response = requests.get(EPG_API_URL.format(unix=unix_time), timeout=10)
        response.raise_for_status()
        data = response.json()

        return data.get("result")

    except requests.exceptions.RequestException as e:
        print(f"Une erreur réseau est survenue : {e}")
        return None
    except ValueError:
        print("Erreur lors de l'analyse de la réponse JSON.")
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
        print("Aucun programme disponible dans le guide EPG.")
        return {
            'start_date': original_start_date,
            'end_date': original_end_date,
            'title': None,
            'program': None
        }

    # Create choices list with program information
    program_choices = []
    for program in programs:
        # Extract the live data from the program
        live_data = program.get("live", program)
        title = live_data.get('title', 'Sans titre')
        start_time = datetime.datetime.fromtimestamp(live_data.get('start', 0))
        end_time = datetime.datetime.fromtimestamp(live_data.get('end', 0))
        duration_min = (end_time - start_time).total_seconds() / 60

        choice_name = (
            f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')} | "
            f"{title} ({int(duration_min)} min)"
        )
        program_choices.append({
            "name": choice_name,
            "value": program  # Store the full program object
        })

    # Add option to keep original selection
    program_choices.insert(0, {
        "name": (
            f"Garder la sélection manuelle originale "
            f"({original_start_date.strftime('%Y-%m-%d %H:%M:%S')} - "
            f"{original_end_date.strftime('%Y-%m-%d %H:%M:%S')})"
        ),
        "value": None
    })

    questions = [
        {
            "type": "list",
            "message": "Sélectionnez un programme ou gardez votre sélection manuelle :",
            "choices": program_choices,
            "long_instruction": "Utilisez les flèches pour naviguer, Entrée pour sélectionner.",
        }
    ]

    try:
        result = prompt(questions)
        if not result:
            return None

        selected_program = result[0]

        # If user chose to keep original selection
        if selected_program is None:
            print("\n✅ Sélection manuelle conservée")
            return {
                'start_date': original_start_date,
                'end_date': original_end_date,
                'title': None,
                'program': None
            }

        # Extract live data and convert program timestamps to datetime objects
        live_data = selected_program.get('live', selected_program)
        program_start = datetime.datetime.fromtimestamp(live_data.get('start', 0))
        program_end = datetime.datetime.fromtimestamp(live_data.get('end', 0))
        program_title = live_data.get('title', 'Sans titre')

        print("\n✅ Programme sélectionné :")
        print(f"  - Titre : {program_title}")
        print(f"  - Début : {program_start.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  - Fin : {program_end.strftime('%Y-%m-%d %H:%M:%S')}")

        return {
            'start_date': program_start,
            'end_date': program_end,
            'title': program_title,
            'program': selected_program
        }

    except KeyboardInterrupt:
        print("\nOpération annulée par l'utilisateur.")
        return None
