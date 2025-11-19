# OqeeRewind - Oqee TV Live Downloader

## Legal Warning

This application is not endorsed by or affiliated with Oqee. This application enables you to download videos for offline viewing which may be forbidden by law in your country. The usage of this application may also cause a violation of the Terms of Service between you and the stream provider. This tool is not responsible for your actions; please make an informed decision before using this application.

## Installation

### Prerequisites
- Python 3.9+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Go ([Installation Guide](https://go.dev/doc/install))
- ffmpeg
- mp4ff-decrypt
```bash
go install github.com/Eyevinn/mp4ff/cmd/mp4ff-decrypt@latest
```

### Steps
Clone the repository and install dependencies:

**Using uv (recommended - faster):**
```bash
git clone https://github.com/NohamR/OqeeRewind && cd OqeeRewind
uv sync
```

**Using pip:**
```bash
git clone https://github.com/NohamR/OqeeRewind && cd OqeeRewind
pip install -r requirements.txt
```

### Configuration
Create a `.env` file in the root directory and add your Oqee credentials (otherwise the script will try to use IP login first):
```bash
OQEE_USERNAME=your_username
OQEE_PASSWORD=your_password
```

Optionally, you can set the following environment variables in the `.env` file:
```bash
OUTPUT_DIR=./downloads
API_KEY=your_api_key_here
API_URL=https://example.com/get-cached-keys
```

## Usage
### Via Command Line

**Using uv:**
```bash
uv run main.py
```

**Using Python directly:**
```bash
python main.py
```

### Via CLI Arguments
```bash
uv run main.py --output-dir ./downloads -id channel_id --start DATE --end DATA -sv best -sa best
```

## DRM Decryption

### Instructions (Widevine)
In order to decrypt DRM content, you will need to have a dumped CDM, after that you will need to place the CDM files into the `./widevine/` directory. For legal reasons we do not include the CDM with the software, and you will have to source one yourself.

## Todo
- [x] Bruteforce implementation
- [x] EPG info support
- [x] License
- [ ] Better README
    - [x] Lib used
    - [x] How to use
    - [x] Lib to install (pip + mp4ff + ffmpeg) 
    - [ ] Demo GIF
- [ ] Lint code
- [ ] Oqee widevine license implementation (.wvd) + mention README
- [ ] Full implementation
- [ ] Verify mp4ff installation
- [ ] CLI arguments implementation + documentation
- [ ] French/English full translation
- [ ] Better output system
- [ ] Add more comments in the code
- [ ] Logging system
- [ ] Live direct restream support


## Libraries Used
- [**aiohttp**](https://github.com/aio-libs/aiohttp) - Async HTTP client/server framework
- [**InquirerPy**](https://github.com/kazhala/InquirerPy) - Interactive command line prompts
- [**python-dotenv**](https://github.com/theskumar/python-dotenv) - Environment variable management
- [**pywidevine**](https://github.com/rlaphoenix/pywidevine) - Widevine CDM implementation
- [**Requests**](https://github.com/psf/requests) - HTTP library