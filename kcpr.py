from typing import Tuple
import logging
import coloredlogs
import sys
from playwright.sync_api import sync_playwright, Browser, Page

# Log initializers
coloredlogs.install(level=logging.INFO)
logger = logging.getLogger(__name__)

class KcprHandler:
    """
    A handler class to interact with the KCPR website and retrieve the currently playing song information.
    Attributes:
        kcpr_uri (str): The URI of the KCPR website.
    Methods:
        get_now_playing() -> Tuple[str, str]:
            Retrieves the artist name and song title of the currently playing song from the KCPR website.
    """

    def __init__(self):
        """
        Initializes the Kcpr class with the KCPR website URI.

        Attributes:
            kcpr_uri (str): The URI of the KCPR website.
        """
        self.kcpr_uri: str = "https://kcpr.org/"

    def get_now_playing(self) -> Tuple[str, str]:
        """
        Retrieves the currently playing song's artist name and title from the KCPR website.
        Uses the Playwright library to open a headless browser, navigate to the KCPR page, and extract
        the artist name and song title from the page's HTML content.
        Returns:
            Tuple[str, str]: A tuple containing the artist name and song title.
        Raises:
            AssertionError: If the artist name or song title cannot be extracted.
        """

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

            logger.info(f"Artist: {artist_name}, Song: {song_title}")

            # Close browser to free resources
            browser.close()

            return (artist_name, song_title)
            
        return None
