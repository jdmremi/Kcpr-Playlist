import undetected_chromedriver as uc
from seleniumbase import Driver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from typing import Tuple


class KcprHandler:
    """
    A handler class to interact with the KCPR streaming service and retrieve the currently playing song.

    Attributes:
        driver (Driver): The web driver used to interact with the KCPR website.
        driver_timeout (int): The timeout duration for the web driver.
        kcpr_uri (str): The URI of the KCPR streaming service.

    Methods:
        get_now_playing() -> Tuple[str, str]:
            Retrieves the currently playing song and artist from the KCPR streaming service.
    """

    def __init__(self):
        self.driver: Driver = Driver(headless=True, uc=True, no_sandbox=True)
        self.driver_timeout: int = 10
        self.kcpr_uri: str = "https://streamdb8web.securenetsystems.net/ce/KCPR1"

    def get_now_playing(self) -> Tuple[str, str]:
        """
        Retrieves the currently playing song and artist from the KCPR website.

        This method uses Selenium WebDriver to navigate to the KCPR website and scrape the
        currently playing song and artist information. It waits explicitly for the song title
        element to be visible to handle any scraping prevention mechanisms on the website.

        Returns:
            Tuple[str, str]: A tuple containing the artist name and song title if found.
            None: If the request times out or the elements are not found.

        Raises:
            TimeoutException: If the request to the KCPR website exceeds the specified timeout.
        """
        # Make request
        self.driver.get(self.kcpr_uri)

        try:
            # Explicit wait for song title to load since there is some scraping prevention on the website.
            WebDriverWait(self.driver, self.driver_timeout).until(
                EC.visibility_of_element_located(
                    (By.ID, "songTitle")))

            artist: str = self.driver.find_element(By.ID, "songArtist")
            song: str = self.driver.find_element(By.ID, "songTitle")

            return (artist.text, song.text)

        except TimeoutException:
            print("Timeout exceeded")

        return None
