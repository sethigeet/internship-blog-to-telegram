# Internship Blog to Telegram

This repository contains a simple script that automates the process of fetching posts from the internship blog/placement blog and sends the new entries to a Telegram channel or group via a Telegram Bot.

---

## Features (Inferred)

- Fetch internship blog posts (likely via HTTP requests or feed parsing).
- Detect new posts and avoid duplicates.
- Format and send updates to a Telegram channel/group using a bot.
- Automatically runs every 5 mins in the background without needing to setup a separate cron job

---

## Prerequisites

- Python (recommend 3.10+)
- A Telegram Bot Token (create via [BotFather](https://t.me/BotFather))
- Target Telegram Chat ID (channel, group, or user)

---

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/sethigeet/internship-blog-to-telegram.git
cd internship-blog-to-telegram
```

### 2. Create and Activate a Virtual Environment (Recommended)

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Variables

Fill in the required variables at the top of the `main.py` script with values that you acquired from Telegram.

### 5. Run the Script without the `headless` mode

```bash
python main.py --no-headless
```

This will launch the browser window and allow you to login using your SSO credentials. These credentials are then saved locally for later use.
Once done, the process will scrape the blog for all the new posts and will sleep after which you should kill the process.

### 6. Run in `headless` mode

Once you have everything setup, you can just run the script manually and it will keep checking the blog regularly.

```bash
python main.py
```

> I would recommend to setup the app as a systemd service or use a tool like `pm` to automatically restart the app if it ever crashes and to be able to run it in the background easily!
