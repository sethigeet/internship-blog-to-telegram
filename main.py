import asyncio
import os
import pickle

import html2text
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium_stealth import stealth
from telethon import TelegramClient, events

# --- CONFIGURATION ---
LAST_POST_FILE = "last_post_url.txt"
API_ID = 123456
API_HASH = "<fill me>"
CHAT_ID = 123456
BOT_TOKEN = "<fill me>"
# --- END CONFIGURATION ---


def save_cookies(driver, location):
    """Saves cookies to a file."""
    with open(location, "wb") as file:
        pickle.dump(driver.get_cookies(), file)


def load_cookies(driver, location):
    """Loads cookies from a file."""
    with open(location, "rb") as file:
        cookies = pickle.load(file)
        for cookie in cookies:
            driver.add_cookie(cookie)


def get_last_post_url():
    """Reads the URL of the last scraped post from a file."""
    if not os.path.exists(LAST_POST_FILE):
        return None
    with open(LAST_POST_FILE, "r") as file:
        return file.read().strip()


def save_last_post_url(url):
    """Saves the URL of the most recent post to a file."""
    with open(LAST_POST_FILE, "w") as file:
        file.write(url)


async def send_posts_to_telegram(posts, client: TelegramClient):
    """
    Sends a list of new blog posts to a specified Telegram chat using Telethon.
    """
    print(f"Connecting to Telegram to send {len(posts)} new post(s)...")

    for post in reversed(posts):
        message = f"📢 **New Internship Blog Post** 📢\n\n**Title:** {post['title']}\n\n**Content:**\n{post['content']}\n\n**Link:** {post['link']}"

        try:
            await client.send_message(CHAT_ID, message)
            print(f"Sent post: {post['title']}")
        except Exception as e:
            print(f"An error occurred with Telegram: {e}")

        # Avoid rate limits from Telegram
        await asyncio.sleep(1)

    print("Finished sending all new posts to Telegram.")


async def get_new_posts(client: TelegramClient, headless=True):
    """
    Scrapes the blog for new posts since the last run and sends them to Telegram.
    """
    print("Starting blog scraper...")

    options = Options()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("start-maximized")
    options.add_argument("user-data-dir=selenium")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(options=options)

    stealth(
        driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )

    cookies_location = "cookies.pkl"
    last_post_url = get_last_post_url()
    print(f"Last scraped post URL: {last_post_url}")

    new_posts = []

    try:
        driver.get("https://campus.placements.iitb.ac.in/blog/")

        if os.path.exists(cookies_location):
            load_cookies(driver, cookies_location)
            driver.refresh()
        else:
            print("No cookies found. Please log in to the blog in the browser.")
            print("The script will continue once you have logged in.")
            wait = WebDriverWait(driver, 300)
            wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//a[contains(text(), 'Internship Blog 2025-26')]")
                )
            )
            save_cookies(driver, cookies_location)
            print("Login successful, cookies saved.")

        driver.get(
            "https://campus.placements.iitb.ac.in/blog/internship/authinternship/"
        )
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "article"))
        )

        scraping_done = False

        while not scraping_done:
            posts_on_page = driver.find_elements(By.TAG_NAME, "article")

            if not posts_on_page:
                print("No posts found on the page. The layout might have changed.")
                break

            for post_element in posts_on_page:
                try:
                    title_element = post_element.find_element(
                        By.CLASS_NAME, "entry-title"
                    )
                    link_element = title_element.find_element(By.TAG_NAME, "a")
                    link = link_element.get_attribute("href")

                    if link == last_post_url:
                        print("Found the last scraped post. Stopping scrape.")
                        scraping_done = True
                        break

                    # Open post in a new tab to get full content
                    driver.execute_script("window.open(arguments[0]);", link)
                    driver.switch_to.window(driver.window_handles[1])

                    WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "entry-content"))
                    )

                    post_soup = BeautifulSoup(driver.page_source, "lxml")
                    h1 = post_soup.find("h1", class_="entry-title")
                    if h1 is None:
                        print("Unable to find title of the blog post...")
                        continue
                    title = h1.get_text(strip=True)
                    content_html = post_soup.find("div", class_="entry-content")

                    # Convert HTML content to Markdown
                    h = html2text.HTML2Text()
                    h.ignore_links = False
                    content_markdown = h.handle(str(content_html))

                    new_posts.append(
                        {"title": title, "link": link, "content": content_markdown}
                    )

                    # Close tab and switch back
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])

                except NoSuchElementException:
                    continue

            if scraping_done:
                break

            # try:
            # next_button = driver.find_element(By.CLASS_NAME, "next")
            # driver.execute_script("arguments[0].click();", next_button)
            # time.sleep(3)
            # except NoSuchElementException:
            # print("No 'next' button found. Assuming it's the only page.")
            # scraping_done = True
    except Exception as e:
        print(f"An error occurred during scraping: {e}")
        await client.send_message(CHAT_ID, f"**Scraper Error:**\n\n`{e}`")
    finally:
        print("Scraping process finished.")
        driver.quit()

    if new_posts:
        print(f"Found {len(new_posts)} new post(s).")
        save_last_post_url(new_posts[0]["link"])
    else:
        print("No new blog posts found.")
    return new_posts


async def main(headless=True):
    """
    Main function to run the scraper periodically and send new posts.
    """
    if not all([API_ID, API_HASH, CHAT_ID]):
        print("Error: API_ID, API_HASH, and CHAT_ID must be set.")
        return

    client = TelegramClient("intern_blog_scraper_sess", API_ID, API_HASH)
    await client.start(bot_token=BOT_TOKEN)

    @client.on(events.NewMessage(chats=CHAT_ID, pattern="(?i)^/refresh$"))
    async def refresh_handler(event):
        """Handles the '/refresh' command."""
        print("--- Force refresh triggered by user ---")
        await event.reply("Force refreshing...")
        try:
            new_posts = await get_new_posts(client, headless=headless)
            if new_posts:
                await send_posts_to_telegram(new_posts, client)
                await event.reply(f"Found and sent {len(new_posts)} new posts.")
            else:
                await event.reply("No new posts found.")
            print("--- Force refresh finished ---")
        except Exception as e:
            print(f"An error occurred during force refresh: {e}")
            await event.reply(f"**Refresh Error:**\n\n`{e}`")

    async with client:
        print("Telegram client connected.")
        # Optional: Send a startup message
        await client.send_message(
            CHAT_ID,
            "Scraper bot started. Checking for new posts every 5 minutes. Send '/refresh' to force a check.",
        )

        while True:
            try:
                print("\n--- Checking for new posts ---")
                new_posts = await get_new_posts(client, headless=headless)

                if new_posts:
                    await send_posts_to_telegram(new_posts, client)
                else:
                    print("No new posts found this time.")

                print(
                    "--- Check finished. Waiting for 5 minutes before next check. ---"
                )
                await asyncio.sleep(300)  # Wait for 5 minutes

            except Exception as e:
                print(f"An error occurred in the main loop: {e}")
                await client.send_message(CHAT_ID, f"**Main Loop Error:**\n\n`{e}`")
                print("Restarting check in 5 minutes...")
                await asyncio.sleep(300)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Scrape IITB Internship Blog and send new posts to Telegram."
    )
    parser.add_argument(
        "--no-headless",
        action="store_false",
        dest="headless",
        help="Run the browser in non-headless mode for debugging.",
    )
    args = parser.parse_args()

    try:
        asyncio.run(main(headless=args.headless))
    except KeyboardInterrupt:
        print("\nScript stopped by user.")
