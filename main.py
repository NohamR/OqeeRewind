"""Main module for Oqee channel selection and stream management."""
from pprint import pprint

import requests
from InquirerPy import prompt
from InquirerPy.validator import EmptyInputValidator
from InquirerPy.base.control import Choice

from utils.stream import (
    get_manifest,
    parse_mpd_manifest,
    organize_by_content_type
)

SERVICE_PLAN_API_URL = "https://api.oqee.net/api/v6/service_plan"

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
            {"name": f"{channel_info.get('name', 'Nom inconnu')}", "value": channel_id}
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


if __name__ == "__main__":
    try:
        selected_channel = select_oqee_channel()

        if selected_channel:
            print("\n✅ Chaîne sélectionnée :")
            print(f"  - Nom : {selected_channel.get('name')}")
            print(f"  - ID : {selected_channel.get('id')}")

            dash_id = selected_channel.get('streams', {}).get('dash')
            if dash_id:
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
                    print("\n✅ Sélection finale terminée. Voici les flux choisis :")
                    pprint(final_selections)
                else:
                    print("\nAucun flux n'a été sélectionné.")

            else:
                print("Aucun flux DASH trouvé pour cette chaîne.")

    except KeyboardInterrupt:
        print("\n\nProgramme interrompu par l'utilisateur. Au revoir !")
