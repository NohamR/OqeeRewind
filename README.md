<p align="center">
    <img src="docs/images/logo_bg.png" width="256"> <a href="https://github.com/NohamR/OqeeRewind">OqeeRewind</a>
    <br/>
    <sup><em>Oqee TV Live Downloader</em></sup>
</p>

<p align="center">
    <a href="https://github.com/NohamR/OqeeRewind/blob/master/LICENSE">
        <img src="https://img.shields.io/:license-MIT-blue.svg" alt="License">
    </a>
    <a href="https://github.com/astral-sh/uv">
        <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Onyx-Nostalgia/uv/refs/heads/fix/logo-badge/assets/badge/v0.json" alt="Manager: uv">
    </a>
    <a href="https://deepwiki.com/NohamR/OqeeRewind"><img src="https://deepwiki.com/badge.svg" alt="Ask DeepWiki"></a>
    <br>
    <a href="README.fr.md">Français</a> | English
</p>

## Legal Warning

This application is not endorsed by or affiliated with Oqee. This application enables you to download videos for offline viewing which may be forbidden by law in your country. The usage of this application may also cause a violation of the Terms of Service between you and the stream provider. This tool is not responsible for your actions; please make an informed decision before using this application.

## Installation

### Prerequisites
- Python 3.9+
- [uv](https://docs.astral.sh/uv/)
- Go ([Installation Guide](https://go.dev/doc/install))
- ffmpeg
- [mp4ff-decrypt](https://github.com/Eyevinn/mp4ff)
```bash
go install github.com/Eyevinn/mp4ff/cmd/mp4ff-decrypt@latest
```

### Steps
Clone the repository and install dependencies:

```bash
git clone https://github.com/NohamR/OqeeRewind && cd OqeeRewind
uv sync
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

### Interactive Mode
If you run the script without arguments, it will guide you through channel selection and date picking.

```bash
uv run main.py
```
https://github.com/user-attachments/assets/54a50828-c0e9-4a29-81c7-e188c238a998


### CLI Mode
You can automate the download by providing arguments.

```bash
usage: main.py [-h] [--start-date START_DATE] [--end-date END_DATE] [--duration DURATION]
               [--channel-id CHANNEL_ID] [--video VIDEO] [--audio AUDIO] [--title TITLE]
               [--username USERNAME] [--password PASSWORD] [--key KEY]
               [--output-dir OUTPUT_DIR] [--widevine-device WIDEVINE_DEVICE]
               [--bruteforce-batch-size BRUTEFORCE_BATCH_SIZE]
               [--segment-batch-size SEGMENT_BATCH_SIZE]
               [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}]

options:
  -h, --help            show this help message and exit
  --start-date START_DATE
                        Start date and time in YYYY-MM-DD HH:MM:SS format
  --end-date END_DATE   End date and time in YYYY-MM-DD HH:MM:SS format
  --duration DURATION   Duration in HH:MM:SS format (alternative to --end-date)
  --channel-id CHANNEL_ID
                        Channel ID to download from
  --video VIDEO         Video quality selection (e.g., 'best', '1080p', '720p', '1080p+best', '720p+worst')
  --audio AUDIO         Audio track selection (e.g., 'best', 'fra_main')
  --title TITLE         Title for the download (default: channel_id_start_date)
  --username USERNAME   Oqee username for authentication
  --password PASSWORD   Oqee password for authentication
  --key KEY             DRM key for decryption (can be specified multiple times)
  --output-dir OUTPUT_DIR
                        Output directory for downloaded files (default: ./downloads)
  --widevine-device WIDEVINE_DEVICE
                        Path to Widevine device file (default: ./widevine/device.wvd)
  --bruteforce-batch-size BRUTEFORCE_BATCH_SIZE
                        Batch size for bruteforce (default: 20000)
  --segment-batch-size SEGMENT_BATCH_SIZE
                        Batch size for segment downloads (default: 64)
  --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set the logging level (default: INFO)
```
https://github.com/user-attachments/assets/cc76990a-3d13-4be1-bb3c-ba8d87e6eaba


#### Examples

**Download a specific program with duration:**
```bash
uv run main.py --channel-id 536 --start-date "2025-12-19 12:00:00" --duration "01:30:00" --video "1080p+best" --audio "best" --title "Record"
```

**Download with manual DRM keys:**
```bash
uv run main.py --channel-id 536 --start-date "2025-12-19 12:00:00" --duration "00:05:00" --key "KID:KEY" --key "KID2:KEY2"
```

## DRM Decryption

### Instructions (Widevine)
In order to decrypt DRM content, you will need to have a dumped CDM, after that you will need to place the CDM files into the `./widevine/` directory. For legal reasons we do not include the CDM with the software, and you will have to source one yourself.

## Todo

### Completed
- [x] Bruteforce implementation
- [x] EPG info support
- [x] License
- [x] Lint code
- [x] Oqee Widevine license implementation (.wvd)
- [x] Full implementation
- [x] Verify mp4ff installation
- [x] CLI arguments implementation + documentation
- [x] French/English full translation
- [x] Add more comments in the code
- [x] Logging system
- [x] README improvements:
    - [x] Libraries used
    - [x] Usage instructions
    - [x] Installation requirements (pip + mp4ff + ffmpeg)
    - [x] Demo GIF

### In Progress
- [ ] Better output system
- [ ] Live direct restream support


## Libraries Used
- [**aiohttp**](https://github.com/aio-libs/aiohttp) - Async HTTP client/server framework
- [**InquirerPy**](https://github.com/kazhala/InquirerPy) - Interactive command line prompts
- [**python-dotenv**](https://github.com/theskumar/python-dotenv) - Environment variable management
- [**pywidevine**](https://github.com/rlaphoenix/pywidevine) - Widevine CDM implementation
- [**Requests**](https://github.com/psf/requests) - HTTP library
