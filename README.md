# WhatsApp Message Automation

> A lightweight Python script using Selenium to automate repetitive message sending on WhatsApp Web.

---

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage Walkthrough](#usage-walkthrough)
- [Configuration & Customization](#configuration--customization)
- [Known Limitations](#known-limitations)
- [Disclaimer](#disclaimer)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

**WhatsApp Message Automation** is a simple Python tool designed to automate sending a repeated message to a single contact or group on WhatsApp Web. 

The script launches Google Chrome via Selenium, prompts the user for the message text and repetition count in the terminal, and pauses to allow the user to manually scan the WhatsApp Web QR code and select the target chat. Once confirmed, it automatically inputs and dispatches the specified message in a loop.

This tool is designed for basic automation tasks, such as sending recurring reminders or testing message delivery in personal chats.

---

## Features

- **Custom Repeat Count**: Specify exact number of message iterations via terminal prompt.
- **Custom Message Text**: Enter any plain text message to send repeatedly.
- **Interactive Login & Chat Selection**: Allows manual QR code authentication and precise chat selection before execution begins.
- **Targeted Messaging**: Sends messages directly to the active chat window opened by the user.

---

## Tech Stack

- **Language**: Python 3
- **Automation Framework**: [Selenium WebDriver](https://www.selenium.dev/)
- **Browser & Driver**: Google Chrome & ChromeDriver

---

## Prerequisites

Before running the script, ensure you have the following installed:

1. **Python 3.x**: [Download Python](https://www.python.org/downloads/)
2. **Google Chrome**: Latest version of the Google Chrome browser.
3. **ChromeDriver**: A `chromedriver` executable matching your installed Chrome version, added to your system `PATH` or placed in the project root directory.
4. **WhatsApp Account**: An active WhatsApp account on a smartphone with WhatsApp Web capability.

---

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/Mzaq1559/Whatsapp-message-automation.git
   cd Whatsapp-message-automation
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## Usage Walkthrough

1. **Run the Script**:
   Execute the script from your terminal:
   ```bash
   python whatsapp_msg_automation.py
   ```

2. **Provide Terminal Inputs**:
   - When prompted, enter the number of times to repeat the message (`repeat_count`).
   - Enter the text message you wish to send.

3. **Scan QR Code & Select Chat**:
   - A Chrome browser window will automatically open to [https://web.whatsapp.com](https://web.whatsapp.com).
   - Scan the QR code using WhatsApp on your phone (if you are not already logged in).
   - Manually click and open the target contact or group chat where you want the messages sent.

4. **Start Automation**:
   - Return to your terminal and press `ENTER` to signal readiness.
   - The script will locate the chat text box and begin sending your message `repeat_count` times automatically.

---

## Configuration & Customization

The script (`whatsapp_msg_automation.py`) can be modified directly for custom behavior:

- **Element Timeout**:
  The script uses `WebDriverWait(driver, 30)` to locate the text box. If your internet connection or browser load time is slow, you can increase the timeout parameter (e.g., `WebDriverWait(driver, 60)`).

- **Adding Inter-Message Delay**:
  To add a delay between consecutive messages, locate the commented-out sleep line in the message loop:
  ```python
  # time.sleep(0.005)
  ```
  Uncomment it and adjust the delay in seconds (e.g., `time.sleep(0.5)`) to pace the message sends.

- **Updating DOM Selectors**:
  WhatsApp Web periodically updates its frontend layout. If the script fails to locate the text area, update the XPath selector in the code:
  ```python
  '//div[@contenteditable="true"][@data-tab="10"]'
  ```

---

## Known Limitations

- **Manual Intervention Required**: Requires manual QR code scanning and manual chat selection before execution (not fully headless).
- **Single-Chat Scope**: Sends messages only to the currently open chat; does not support multi-contact broadcasting or contact lists.
- **No Templating or Placeholders**: Sends exact static text without dynamic variable replacement or CSV data inputs.
- **UI Fragility**: Relies on specific WhatsApp Web DOM XPath selectors, which may break when WhatsApp updates its web interface.
- **Basic Error Handling**: Does not feature automated retry mechanisms for lost network connections or closed browser windows.

---

## Disclaimer

> [!WARNING]
> This tool automates a personal WhatsApp Web session. Automated messaging or spamming may violate [WhatsApp's Terms of Service](https://www.whatsapp.com/legal/terms-of-service) and can result in your phone number being temporary or permanently banned.
> 
> Use this tool responsibly, for personal educational purposes only, and at your own risk. The author assumes no liability for any misuse or account restrictions.

---

## Contributing

Contributions, bug reports, and feature suggestions are welcome! Please review [CONTRIBUTING.md](CONTRIBUTING.md) before submitting pull requests or issues.

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
