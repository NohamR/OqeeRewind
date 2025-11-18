"""OQEE streaming service client for authentication and content access."""
import base64
import logging
import os
from urllib.parse import urlparse, parse_qs

from dotenv import load_dotenv

load_dotenv()


class _LoggerProxy:
    """Lightweight logger helper that returns exceptions for raise statements."""

    def __init__(self, name: str):
        self._logger = logging.getLogger(name)

    def info(self, message: str):
        """Log an info message."""
        self._logger.info(message)

    def error(self, message: str) -> RuntimeError:
        """Log an error message and return a RuntimeError."""
        self._logger.error(message)
        return RuntimeError(message)

class OqeeClient:  # pylint: disable=too-many-instance-attributes
    """
    Service code for OQEE streaming service (https://oqee.com).

    Authorization: Credentials/IP
    Security: 1080p@L1 720@L3
    """

    def __init__(self, ctx, movie, title):
        super().__init__(ctx)
        self.session = None  # Will be set by parent class
        self.log = _LoggerProxy(self.__class__.__name__)
        self.movie = movie
        self.title, self.typecontent = self.parse_title(title)

        # Base headers template for API requests
        self._headers_template = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'priority': 'u=0, i',
            'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
        }
        self.headers_base = self._build_headers()

        # Headers for API requests
        self.headers = None

        # Headers for manifest/licence
        self.headers_auth = None

        self.access_token = None
        self.right_token = None
        self.profil_id = None
        self.lic_url = None

        self.configure()


    def parse_title(self, title):
        """
        Parse and categorize different types of OQEE TV URLs.
        Args:
            title (str): The URL or title string to parse. Can be a full OQEE TV URL or a partial path.
        Returns:
            tuple or str: If the URL matches a known pattern, returns a tuple of (content_id, content_type).
                         If no pattern matches, returns the original title string.
        """
        if title is None:
            raise self.log.error("No title provided.")

        title = title.replace("https://oqee.tv", "").replace("/play", "")
        if title.startswith("/replay_collection/"):
            return (
                title.replace("/replay_collection/", "").replace("/all", ""),
                "replay_collection"
            )
        if title.startswith("/vod/contents/"):
            return title.replace("/vod/contents/", ""), "vod"
        if title.startswith("/svod/portal/"):
            return title.replace("/svod/portal/", "").split("/")[1],  "vod"
        if title.startswith("/replay/"):
            return title.replace("/replay/", ""), "replay"
        return title


    def _extract_title_id(self, title):
        """Return a usable identifier regardless of input structure."""
        if title is None:
            raise self.log.error("Title identifier is required")
        if isinstance(title, dict):
            return title.get('id') or title.get('program_id') or title.get('content_id')
        return getattr(title, 'id', title)


    def get_vod(self, title):
        """Fetch VOD playback information and return the raw API response."""
        title_id = self._extract_title_id(title)
        data = {
            "supported_stream_types": ["dash"],
            "supported_drms": ["widevine"],
            "supported_ciphers": ["cbcs", "cenc"],
            "supported_ads": ["vast", "vmap"],
        }
        response = self.session.post(
            f'https://api.oqee.net/api/v1/svod/offers/{title_id}/playback_infos',
            headers=self.headers_auth,
            json=data,
        ).json()
        self.lic_url = response['result']['license_server']
        return response


    def get_vod_info(self):
        """Return the raw VOD metadata payload for the current title."""
        response = self.session.get(
            f'https://api.oqee.net/api/v3/vod/contents/{self.title}',
            headers=self.headers_base,
        ).json()
        if response['success'] is False:
            raise self.log.error(f"Failed to get the replay: {response['message']}")
        return response


    def get_replay(self, title):
        """Fetch replay playback information and return the raw API response."""
        title_id = self._extract_title_id(title)
        payload = {
            'program_id': title_id,
            'supported_stream_types': ['dash'],
            'supported_drms': ['widevine'],
            'supported_ciphers': ['cenc'],
            'supported_subs': ['ttml', 'vtt'],
            'supported_ads': ['vast', 'vmap'],
        }
        response = self.session.post(
            f'https://api.oqee.net/api/v1/replay/programs/{title_id}/playback_infos',
            headers=self.headers_auth,
            json=payload,
        ).json()
        if response['success'] is False:
            raise self.log.error(f"Failed to get the replay: {response['message']}")
        self.lic_url = response['result']['license_server']
        return response


    def get_replay_info(self):
        """
        Retrieve replay information for a given title from the OQEE API.
        """
        response = self.session.get(
            f'https://api.oqee.net/api/v2/replay/programs/{self.title}',
            headers=self.headers_base,
        ).json()
        if response['success'] is False:
            raise self.log.error(f"Failed to get the replay: {response['message']}")
        if response['result']['type'] != 'replay':
            raise self.log.error(f"Provided ID is not a replay: {response['type']}")
        return response


    def get_replay_collection(self):
        """Retrieve replay collection information from Oqee API and return the raw response."""
        response = self.session.get(
            f'https://api.oqee.net/api/v2/pages/replay_collection/{self.title}',
            headers=self.headers_base,
        ).json()
        if response['success'] is False:
            raise self.log.error(f"Failed to get the replay: {response['message']}")
        if response['result']['type'] != 'collection':
            raise self.log.error(f"Provided ID is not a collection: {response['type']}")
        return response


    def get_titles(self):
        """
        Get title information based on content type.
        """
        if self.typecontent == "replay":
            return self.get_replay_info()
        if self.typecontent == "vod":
            return self.get_vod_info()
        if self.typecontent == "replay_collection":
            return self.get_replay_collection()
        return None


    def get_tracks(self, title):
        """
        Get track information based on content type.
        """
        if self.typecontent in ("replay", "replay_collection"):
            return self.get_replay(title)
        if self.typecontent == "vod":
            return self.get_vod(title)
        return None


    def certificate(self, **_):
        """
        Get the Service Privacy Certificate.
        """
        response = self.session.post(
            url=self.lic_url,
            headers=self.headers_auth,
            json={"licenseRequest": "CAQ="}
        )
        return response.json()['result']['license']


    def license(self, challenge, **_):
        """
        Get the License response for the specified challenge and title data.
        """
        license_request = base64.b64encode(challenge).decode()
        response = self.session.post(
            url=self.lic_url,
            headers=self.headers_auth,
            json={'licenseRequest': license_request}
        )
        return response.json()['result']['license']


    def configure(self):
        """Configure the client by logging in and processing title information."""
        self.log.info("Logging in")
        self.login()
        self.log.info(f"Processing title ID based on provided path: {self.title}")
        self.log.info(f"Obtained the {self.typecontent}: {self.title}")

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
            overrides={'authorization': f'Bearer {self.access_token}'}
        )
        data = self.session.get(
            'https://api.oqee.net/api/v3/user/rights_proxad',
            headers=headers
        ).json()
        return data['result']['token']


    def profil(self):
        """
        Gets the first profile ID from the OQEE API.
        """
        headers = self._build_headers(
            overrides={'authorization': f'Bearer {self.access_token}'}
        )
        data = self.session.get(
            'https://api.oqee.net/api/v2/user/profiles',
            headers=headers
        ).json()
        self.log.info("Selecting first profile by default.")
        return data['result'][0]['id']


    def login_cred(self, username, password):
        """Authenticate with OQEE service using Free account credentials."""
        headers = self._build_headers(overrides={
            'accept-language': 'fr-FR,fr;q=0.8',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'sec-ch-ua': '"Brave";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'x-oqee-customization': '0',
        })
        data = {"provider":"free","platform":"web"}
        response = self.session.post('https://api.oqee.net/api/v2/user/oauth/init', headers=headers, json=data).json()
        redirect_url = response['result']['redirect_url']
        r = parse_qs(urlparse(redirect_url).query)
        client_id = r['client_id'][0]
        redirect_uri = r['redirect_uri'][0]
        state = r['state'][0]

        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9, image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.7',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://subscribe.free.fr',
            'Referer': 'https://subscribe.free.fr/auth/auth.pl?',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Sec-GPC': '1',
            'Upgrade-Insecure-Requests': '1',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Brave";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
        }
        data = {
            'login': username,
            'pass': password,
            'ok': 'Se connecter',
            'client_id': client_id,
            'ressource': '',
            'response_type': 'code',
            'redirect_uri': redirect_uri,
            'state': state
        }
        r = self.session.post('https://subscribe.free.fr/auth/auth.pl', headers=headers, data=data)
        parsed_url = parse_qs(urlparse(r.url).query)
        token = parsed_url['result'][0]

        headers = self._build_headers(
            overrides={'x-oqee-customization': '0'},
            remove=('x-oqee-account-provider',)
        )
        data = self.session.post(
            'https://api.oqee.net/api/v5/user/login',
            headers=headers,
            json={'type': 'freeoa', 'token': token}
        ).json()
        return data['result']['token']


    def login_ip(self):
        """
        Performs IP-based authentication with the OQEE service.
        """
        headers = self._build_headers(
            overrides={'x-oqee-customization': '0'},
            remove=('x-oqee-account-provider',)
        )
        data = {"type": "ip"}
        data = self.session.post(
            'https://api.oqee.net/api/v5/user/login',
            headers=headers,
            json=data
        ).json()
        return data['result']['token']


    def login(self):
        """
        Log in to the Oqee service and set up necessary tokens and headers.
        """
        username = os.getenv("OQEE_USERNAME")
        password = os.getenv("OQEE_PASSWORD")

        if not username or not password:
            self.log.info("No environment credentials found, using IP login by default.")
            self.access_token = self.login_ip()
        else:
            self.log.info("Logging in with credentials sourced from environment variables")
            self.access_token = self.login_cred(username, password)

        self.log.info("Fetching rights token")
        self.right_token = self.right()
        self.log.info("Fetching profile ID")
        self.profil_id = self.profil()

        self.headers = self._build_headers(overrides={
            'x-fbx-rights-token': self.right_token,
            'x-oqee-profile': self.profil_id,
        })

        self.headers_auth = self._build_headers(overrides={
            'x-fbx-rights-token': self.right_token,
            'x-oqee-profile': self.profil_id,
            'authorization': f'Bearer {self.access_token}',
        })
