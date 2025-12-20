"""Module for fetching DRM keys and generating PSSH boxes."""
from uuid import UUID
import requests
from pywidevine.cdm import Cdm
from pywidevine.device import Device
from pywidevine.pssh import PSSH


def fetch_drm_keys(kid: str, api_url: str, api_key: str) -> str:
    """Fetch DRM keys for a given KID.

    Args: kid: The key identifier string.
    Returns: The DRM key as a string.
    """
    headers = {
        "Content-Type": "application/json",
        "Api-Key": api_key,
    }
    data = {"service": "oqee", "kid": kid}
    response = requests.post(api_url, headers=headers, json=data, timeout=10)
    return response.json()["key"]


def generate_pssh(kids: list[str]) -> PSSH:
    """Generate a PSSH box for given KIDs.

    Args: kids: List of key identifier strings.
    Returns: The PSSH object.
    """
    default_pssh = (
        "AAAAiHBzc2gAAAAA7e+LqXnWSs6jyCfc1R0h7QAAAGgIARIQrKzUjhLvvbqkebbW2/EQtBIQ"
        "WxKIsxtqP3iaIFYUu9f6xxIQXn4atxoopds39jbUXbiFVBIQUUJpv9uuzWKv4ccKTtooMRIQ"
        "ocf9FUFCoGm775zPIBr3HRoAKgAyADgASABQAA=="
    )
    pssh = PSSH(default_pssh)
    pssh.set_key_ids([UUID(kid.replace("-", "").lower()) for kid in kids])
    return pssh


def get_keys(kids: list[str], method: dict) -> list[str]:
    """Retrieve DRM keys using the specified method."""
    if method["method"] == "api":
        print("Fetching DRM keys via API...")
        keys = []
        for kid in kids:
            key = fetch_drm_keys(kid, method["api_url"], method["api_key"])
            keys.append(f"{kid}:{key}")
        return keys

    print("Fetching DRM keys via Widevine CDM...")
    client = method["client_class"]

    device = Device.load(method["device_file"])
    cdm = Cdm.from_device(device)
    session_id = cdm.open()
    certificate = client.certificate()
    cdm.set_service_certificate(session_id, certificate)

    pssh_data = generate_pssh(kids)
    challenge = cdm.get_license_challenge(session_id, pssh_data, privacy_mode=True)
    license_data = client.license(challenge)

    cdm.parse_license(session_id, license_data)
    keys = []
    for key in cdm.get_keys(session_id):
        if key.type == "CONTENT":
            keys.append(f"{key.kid.hex}:{key.key.hex()}")
    cdm.close(session_id)
    return keys
