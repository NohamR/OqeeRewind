"""OQEE streaming service client for authentication and content access."""

import base64
from urllib.parse import urlparse, parse_qs
import requests

from dotenv import load_dotenv

load_dotenv()


class OqeeClient:  # pylint: disable=too-many-instance-attributes
    """
    Service code for OQEE streaming service (https://oqee.com).

    Authorization: Credentials/IP
    Security: 1080p@L1 720@L3
    """

    def __init__(self, username: str, password: str):
        super().__init__()
        self.session = requests.Session()

        # Base headers template for API requests
        self._headers_template = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "priority": "u=0, i",
            "sec-ch-ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
        }
        self.headers_base = self._build_headers()

        # Headers for API requests
        self.headers = None

        # Headers for manifest/licence
        self.headers_auth = None

        self.access_token = None
        self.right_token = None
        self.profil_id = None
        self.lic_url = "https://license.oqee.net/api/v1/live/license/widevine"

        self.configure(username, password)

    def certificate(self, **_):
        """
        Get the Service Privacy Certificate.
        """
        response = self.session.post(
            url=self.lic_url, headers=self.headers_auth, json={"licenseRequest": "CAQ="}
        )
        return response.json()["result"]["license"]

    def license(self, challenge, **_):
        """
        Get the License response for the specified challenge and title data.
        """
        license_request = base64.b64encode(challenge).decode()
        response = self.session.post(
            url=self.lic_url,
            headers=self.headers_auth,
            json={"licenseRequest": license_request},
        )
        if not response.json()["success"]:
            raise ValueError(
                f"License request failed: {response.json()['error']['msg']}"
            )
        return response.json()["result"]["license"]

    def configure(self, username, password):
        """Configure the client by logging in and processing title information."""
        print("Logging in")
        self.login(username, password)

    def _build_headers(self, overrides=None, remove=None):
        """Clone default headers and apply optional overrides/removals."""
        headers = self._headers_template.copy()
        if overrides:
            headers.update(overrides)
        if remove:
            for key in remove:
                headers.pop(key, None)
        return headers

    def right(self):
        """
        Get user rights token from Oqee API.
        """
        headers = self._build_headers(
            overrides={"authorization": f"Bearer {self.access_token}"}
        )
        data = self.session.get(
            "https://api.oqee.net/api/v3/user/rights_proxad", headers=headers
        ).json()
        return data["result"]["token"]

    def profil(self):
        """
        Gets the first profile ID from the OQEE API.
        """
        headers = self._build_headers(
            overrides={"authorization": f"Bearer {self.access_token}"}
        )
        data = self.session.get(
            "https://api.oqee.net/api/v2/user/profiles", headers=headers
        ).json()
        print("Selecting first profile by default.")
        return data["result"][0]["id"]

    def login_cred(self, username, password):
        """Authenticate with OQEE service using Free account credentials."""
        headers = self._build_headers(
            overrides={
                "accept-language": "fr-FR,fr;q=0.8",
                "cache-control": "no-cache",
                "pragma": "no-cache",
                "priority": "u=1, i",
                "sec-ch-ua": '"Brave";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "x-oqee-customization": "0",
            }
        )
        data = {"provider": "free", "platform": "web"}
        response = self.session.post(
            "https://api.oqee.net/api/v2/user/oauth/init", headers=headers, json=data
        ).json()
        redirect_url = response["result"]["redirect_url"]
        r = parse_qs(urlparse(redirect_url).query)
        client_id = r["client_id"][0]
        redirect_uri = r["redirect_uri"][0]
        state = r["state"][0]

        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9, image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.7",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://subscribe.free.fr",
            "Referer": "https://subscribe.free.fr/auth/auth.pl?",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Sec-GPC": "1",
            "Upgrade-Insecure-Requests": "1",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "sec-ch-ua": '"Brave";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
        }
        data = {
            "login": username,
            "pass": password,
            "ok": "Se connecter",
            "client_id": client_id,
            "ressource": "",
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": state,
        }
        r = self.session.post(
            "https://subscribe.free.fr/auth/auth.pl", headers=headers, data=data
        )
        parsed_url = parse_qs(urlparse(r.url).query)
        if "result" not in parsed_url:
            raise ValueError(
                "Login failed: invalid credentials or error in authentication"
            )
        token = parsed_url["result"][0]

        headers = self._build_headers(
            overrides={"x-oqee-customization": "0"}, remove=("x-oqee-account-provider",)
        )
        data = self.session.post(
            "https://api.oqee.net/api/v5/user/login",
            headers=headers,
            json={"type": "freeoa", "token": token},
        ).json()
        return data["result"]["token"]

    def login_ip(self):
        """
        Performs IP-based authentication with the OQEE service.
        """
        headers = self._build_headers(
            overrides={"x-oqee-customization": "0"}, remove=("x-oqee-account-provider",)
        )
        data = {"type": "ip"}
        data = self.session.post(
            "https://api.oqee.net/api/v5/user/login", headers=headers, json=data
        ).json()
        return data["result"]["token"]

    def login(self, username, password):
        """
        Log in to the Oqee service and set up necessary tokens and headers.
        """
        if not username or not password:
            print("No credentials provided, using IP login.")
            self.access_token = self.login_ip()
        else:
            print("Logging in with provided credentials")
            try:
                self.access_token = self.login_cred(username, password)
            except ValueError as e:
                print(f"Credential login failed: {e}. Falling back to IP login.")
                self.access_token = self.login_ip()

        print("Fetching rights token")
        self.right_token = self.right()
        print("Fetching profile ID")
        self.profil_id = self.profil()

        self.headers = self._build_headers(
            overrides={
                "x-fbx-rights-token": self.right_token,
                "x-oqee-profile": self.profil_id,
            }
        )

        self.headers_auth = self._build_headers(
            overrides={
                "x-fbx-rights-token": self.right_token,
                "x-oqee-profile": self.profil_id,
                "authorization": f"Bearer {self.access_token}",
            }
        )
