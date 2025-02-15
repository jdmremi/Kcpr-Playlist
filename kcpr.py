import logging
import coloredlogs
import os
import sys
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Browser, Page
from spotify import SpotifyAuthManager
from typing import Tuple, Optional

# Load .env vars
load_dotenv()

# Spotify OAuth manager stuff
CLIENT_ID: str = os.getenv("CLIENT_ID")
CLIENT_SECRET: str = os.getenv("CLIENT_SECRET")
REDIRECT_URI: str = os.getenv("REDIRECT_URI")
SCOPES: str = os.getenv("SCOPES")
USER_ID: str = os.getenv("USER_ID")
PLAYLIST_ID: str = os.getenv("PLAYLIST_ID")

# Interval to check for the currently playing song
INTERVAL: int = 30

# Log initializers
stdout_handler = logging.StreamHandler(sys.stdout)
file_handler = logging.FileHandler('logs.log')
coloredlogs.install(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(stdout_handler)
logger.addHandler(file_handler)

class KcprSpotifyService:
    """
    KcprSpotifyService class provides functionality to monitor and handle the currently playing song on the KCPR website,
    and manage the corresponding Spotify playlist by adding new tracks that are not already in the playlist.

    Methods:
        __init__(): Initializes the KcprSpotifyService class, sets up the SpotifyAuthManager, and fetches the current tracks in the specified Spotify playlist.
        async get_now_playing(page) -> Optional[Tuple[str, str]]: Optional[Tuple[str, str]]: A tuple containing the artist name and song title if successful, otherwise None.
        async monitor_now_playing(): Monitors the currently playing song on the KCPR website and sends the data to the handler.
        async handle_now_playing(artist: str, song: str) -> None: Handles the currently playing song by checking if it is already in the playlist, and if not, adds it to the playlist and logs the event.
    """

    def __init__(self):
        """
        Initializes the Kcpr class.

        Attributes:
            kcpr_uri (str): The URI for the KCPR website.
            prev_data (str): Previously fetched data, initially set to None.
            spotify_handler (SpotifyAuthManager): An instance of SpotifyAuthManager for handling Spotify authentication and API requests.
            spotify_playlist_track_uris (list[str]): A list of track URIs in the Spotify playlist to avoid duplicates.

        Initializes the SpotifyAuthManager with the provided client ID, client secret, redirect URI, scopes, and user ID.
        Fetches the current tracks in the specified Spotify playlist to populate spotify_playlist_track_uris.
        """
        self.kcpr_uri: str = "https://kcpr.org/"
        self.prev_data: str = None
        self.spotify_handler: SpotifyAuthManager = SpotifyAuthManager(
            client_id=CLIENT_ID, client_secret=CLIENT_SECRET, redirect_uri=REDIRECT_URI, scopes=SCOPES, user_id=USER_ID)
        # Used to keep track of the tracks in the playlist to avoid duplicates.
        self.spotify_playlist_track_uris: list[str] = self.spotify_handler.get_playlist_tracks(
            playlist_id=PLAYLIST_ID)

    async def get_now_playing(self, page) -> Optional[Tuple[str, str]]:
        """
        Fetches the currently playing song from the given page.
        Args:
            page: The page object to interact with.
        Returns:
            Optional[Tuple[str, str]]: A tuple containing the artist name and song title if successful, 
            otherwise None.
        Raises:
            Exception: If there is an error fetching the currently playing song.
        """
        try:
            # Wait for div containing songTitle to load
            await page.wait_for_selector("div.ssiEncore_songTitle", timeout=10000)

            # Extract artist name and title
            artist_name: str = await page.locator("div.ssiEncore_songArtist").inner_text()
            song_title: str = await page.locator("div.ssiEncore_songTitle").inner_text()

            assert artist_name and song_title, "Unable to extract artist name and song title."

            return artist_name, song_title

        except Exception as e:
            logger.error(f"Error fetching now playing song: {e}")
            return None

    async def monitor_now_playing(self):
        """
        Monitors the currently playing song on the KCPR website.
        This asynchronous method uses Playwright to open a headless browser and navigate to the KCPR URI.
        It continuously checks the page for the currently playing song and logs the information.
        If a song is found, it sends the artist and song data to the handler.
        The method runs indefinitely, checking for updates every 30 seconds, until it is cancelled.
        Raises:
            asyncio.CancelledError: If the monitoring is stopped.
        Note:
            Ensure that `self.kcpr_uri`, `self.get_now_playing`, and `self.handle_now_playing` are properly defined.
        """
        async with async_playwright() as p:
            browser: Browser = await p.chromium.launch(headless=True)
            page: Page = await browser.new_page()
            await page.goto(self.kcpr_uri, timeout=60000)

            try:
                while True:
                    # Get the currently playing song from the page
                    now_playing = await self.get_now_playing(page)

                    # If we have a currently playing song, then send the data to the handler.
                    if now_playing:
                        artist, song = now_playing
                        await self.handle_now_playing(artist, song)

                    # Wait 30 seconds before checking again
                    await asyncio.sleep(INTERVAL)

            except asyncio.CancelledError:
                logger.warning("Monitoring stopped.")
            finally:
                await browser.close()

    async def handle_now_playing(self, artist: str, song: str) -> None:
        """
        Handles the currently playing song by checking if it is already in the playlist,
        and if not, adds it to the playlist and logs the event.
        Args:
            artist (str): The name of the artist currently playing.
            song (str): The title of the song currently playing.
        Returns:
            None
        """
        # Format the query and remove "(Clean)" if present.
        query: str = f"{artist} - {song}".replace("(Clean)", "").strip()

        # If first request after restarting, set the previous data to the current song.
        if self.prev_data is None:
            self.prev_data = query
        # If we have new data
        if self.prev_data != query:
            # Update the previous data to be currently playing song regardless of whether it's in the playlist.
            self.prev_data = query

            logger.info(f"Now playing: {query}")
            # Get the track from Spotify
            track_uri: str = self.spotify_handler.get_track(
                artist_name=artist, title=song, similarity_threshold=0.30)

            # Get just the track ID from the URI
            track_id: str = track_uri.split(":")[-1]

            # If the track is not in our playlist, then we'll add it.
            if not track_id in self.spotify_playlist_track_uris:

                if track_uri == '':
                    logger.warning(f"Track not found on Spotify: {query}")
                else:
                    # Add the track to the playlist
                    self.spotify_handler.add_track_to_playlist(
                        playlist_id=PLAYLIST_ID, track_id=track_uri)
                    logger.debug(f"Added track to playlist: {query}")

                    # Log the event in the format: DD MM YYYY HH:MM:SS - [query](link to spotify track)
                    # Log to file
                    logger.info(
                        f"{datetime.now()} {query} (https://open.spotify.com/track/{track_id})")

                    # Add the track ID to the playlist track IDs to avoid duplicates.
                    self.spotify_playlist_track_uris.append(track_id)
                    print(self.spotify_playlist_track_uris)


            else:
                logger.warning(f"Track already in playlist: {query}")


async def main():
    kcpr_service: KcprSpotifyService = KcprSpotifyService()
    await kcpr_service.monitor_now_playing()

if __name__ == "__main__":
    asyncio.run(main())
