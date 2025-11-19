"""Main module for Oqee channel selection and stream management."""

from datetime import datetime, timedelta
from utils.input import (
    stream_selection,
    get_date_input,
    get_epg_data_at,
    select_program_from_epg
)

if __name__ == "__main__":
    try:
        selections = stream_selection()
        freebox_id = selections.get("channel", {}).get("freebox_id")
        channel_id = selections.get("channel", {}).get("id")

        start_date, end_date = get_date_input()

        if start_date > datetime.now() - timedelta(days=7):
            epg_data = get_epg_data_at(start_date)

            programs = epg_data["entries"][str(channel_id)]
            program_selection = select_program_from_epg(
                programs,
                start_date,
                end_date
            )
            if program_selection:
                start_date = program_selection['start_date']
                end_date = program_selection['end_date']
                title = program_selection['title']

    except KeyboardInterrupt:
        print("\n\nProgramme interrompu par l'utilisateur. Au revoir !")
