# OqeeRewind - Oqee TV Live Downloader

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

## Libraries Used

- **aiohttp** (3.13.2) - Async HTTP client/server framework
- **InquirerPy** (0.3.4) - Interactive command line prompts
- **python-dotenv** (1.2.1) - Environment variable management
- **pywidevine** (1.9.0) - Widevine CDM implementation
- **Requests** (2.32.5) - HTTP library

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