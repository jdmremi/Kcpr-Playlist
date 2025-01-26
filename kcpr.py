import undetected_chromedriver as uc
from seleniumbase import Driver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from typing import Tuple


class KcprHandler:
    def __init__(self):
        self.driver: Driver = Driver(headless=True, uc=True)
        self.driver_timeout: int = 10
        self.kcpr_uri: str = "https://streamdb8web.securenetsystems.net/ce/KCPR1"

    def get_now_playing(self) -> Tuple[str, str]:
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
