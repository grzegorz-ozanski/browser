# 🧭 Browser Automation Wrapper

Shared module for managing Selenium + Chrome automation in a reusable and platform-aware way across multiple Python scripts.

## ✨ Features

- ✅ Auto-download of ChromeDriver if missing
- ✅ Structured logging with context and timestamps
- ✅ Platform-aware binary detection and setup
- ✅ Centralized log directory management
- ✅ Graceful browser teardown and error handling

## 📋 Requirements

- Python 3.10+
- Google Chrome
- `selenium`
- `zstandard` (used for compressed driver downloads)

## 📦 Installation

```bash
git clone https://github.com/grzegorz-ozanski/browser.git
pip install -r requirements.txt
```

## ⚙️ Configuration

You can customize the logging behavior of any tool using this library by setting the following environment variables:

- **`BROWSER_LOG_LEVEL`** — log level (e.g. `'DEBUG'`, `'INFO'`, etc.) as accepted by the Python `logging` module  
  *default: `'DEBUG'`*

- **`BROWSER_LOG_FORMATTING`** — log message format string  
  *default: `'%(levelname)s:%(name)s %(asctime)s %(message)s'`*

- **`BROWSER_LOG_TO_CONSOLE`** — whether logs should be printed to the console; accepts any value parsable as boolean  
  *default: `'True'`*

- **`BROWSER_LOG_FILENAME`** — path to a log file; if empty (`''`), logging to file is disabled  
  *default: `''`*

## 🗂️ Components

```text
browser/
├── browser.py            # Main wrapper class for Selenium Chrome
├── browseroptions.py     # Predefined Chrome launch options
├── chromedownloader.py   # Auto-downloader of ChromeDriver
├── platforminfo.py       # OS/platform detection
├── weblogger.py          # Contextual structured logging
├── logconfig.py          # Custom logging config
└── log.py                # Helpers for setting up logging
```

## 🙋 Author

Created with ❤️ by [**Grzegorz Ożański**](https://github.com/grzegorz-ozanski)  
with a little help from [ChatGPT](https://chat.openai.com/) — for naming things, formatting logs, and mocking flaky tests 😉

This project is part of my public portfolio — feel free to explore or reuse it.

## 📄 License

MIT License
