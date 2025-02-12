from typing import Tuple
from playwright.sync_api import sync_playwright, Browser, Page

class KcprHandler:

    def __init__(self):
        self.kcpr_uri: str = "https://kcpr.org/"

    def get_now_playing(self) -> Tuple[str, str]:

        with sync_playwright() as p:

            # Init browser and go to KCPR page. Adjust timeout if needed.
            browser: Browser = p.chromium.launch(headless=True)
            page: Page = browser.new_page()
            page.goto(self.kcpr_uri, timeout=60000)

            # Wait for div containing songTitle to load
            page.wait_for_selector("div.ssiEncore_songTitle", timeout=10000)

            # Extract artist name and title of now playing song
            artist_name: str = page.locator("div.ssiEncore_songArtist").inner_text()
            song_title: str = page.locator("div.ssiEncore_songTitle").inner_text()

            assert artist_name != "" and song_title != "", "Unable to extract artist name and song title from KCPR."

            # Close browser to free resources
            browser.close()

            return (artist_name, song_title)
            
        return None
