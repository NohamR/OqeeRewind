"""Main module for Oqee channel selection and stream management."""
from pprint import pprint

import requests
from InquirerPy import prompt
from InquirerPy.validator import EmptyInputValidator
from InquirerPy.base.control import Choice

from utils.input import (
    stream_selection,
    get_date_input,
)

if __name__ == "__main__":
    try:
        selections = stream_selection()
        start_date, end_date = get_date_input()

    except KeyboardInterrupt:
        print("\n\nProgramme interrompu par l'utilisateur. Au revoir !")
