# OqeeRewind - Oqee TV Live Downloader

## Legal Warning

This application is not endorsed by or affiliated with Oqee. This application enables you to download videos for offline viewing which may be forbidden by law in your country. The usage of this application may also cause a violation of the Terms of Service between you and the stream provider. This tool is not responsible for your actions; please make an informed decision before using this application.

## Installation

### Prerequisites
- Python 3.x
- Go ([Installation Guide](https://go.dev/doc/install))
- ffmpeg

### Steps

1. Clone the repository:
```bash
git clone https://github.com/NohamR/OqeeRewind
cd OqeeRewind
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Install mp4ff-decrypt:
```bash
go install github.com/Eyevinn/mp4ff/cmd/mp4ff-decrypt@latest
```

## DRM Decryption

### Instructions (Widevine)
In order to decrypt DRM content, you will need to have a dumped CDM, after that you will need to place the CDM files into the `./widevine/` directory. For legal reasons we do not include the CDM with the software, and you will have to source one yourself.

## Todo
- [x] Bruteforce implementation
- [ ] Better README
    - [ ] Lib used
    - [ ] How to use
    - [ ] Lib to install (pip + mp4ff + ffmpeg) 
    - [ ] Demo GIF
- [x] License
- [ ] Lint code
- [ ] Full implementation
- [ ] Frenc/English full translation
- [ ] Add more comments in the code
- [ ] Oqee widevine license implementation (.wvd) + mention README
- [ ] Better output system
- [ ] Verify mp4ff installation

## Libraries Used
- [**aiohttp**](https://github.com/aio-libs/aiohttp) - Async HTTP client/server framework
- [**InquirerPy**](https://github.com/kazhala/InquirerPy) - Interactive command line prompts
- [**python-dotenv**](https://github.com/theskumar/python-dotenv) - Environment variable management
- [**pywidevine**](https://github.com/rlaphoenix/pywidevine) - Widevine CDM implementation
- [**Requests**](https://github.com/psf/requests) - HTTP library