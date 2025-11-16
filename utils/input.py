import datetime
from InquirerPy import prompt
from prompt_toolkit.validation import Validator, ValidationError

class DatetimeValidator(Validator):
    """
    Validateur personnalisé pour les chaînes datetime au format "YYYY-MM-DD HH:MM:SS".
    """
    def validate(self, document):
        try:
            datetime.datetime.strptime(document.text, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise ValidationError(
                message="Veuillez entrer une date/heure valide au format YYYY-MM-DD HH:MM:SS",
                cursor_position=len(document.text),
            )

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
            h, m, s = [int(part) for part in parts]
            if not (0 <= m < 60 and 0 <= s < 60):
                raise ValueError("Les minutes et les secondes doivent être entre 0 et 59.")
        except ValueError:
            raise ValidationError(
                message="Format invalide. Utilisez HH:MM:SS avec des nombres valides.",
                cursor_position=len(document.text),
            )
        
def get_date_input():
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
            "default": start_date_result["datetime"] if start_date_result else "2025-01-01 12:00:00",
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
                end_date = datetime.datetime.strptime(end_date_result["datetime"], "%Y-%m-%d %H:%M:%S")
                print(f"\nDate/heure de fin : {end_date}")
            except (ValueError, TypeError):
                print("Impossible d'analyser la chaîne de date/heure fournie.")
    return start_date, end_date