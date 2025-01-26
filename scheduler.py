import schedule
import time
import logging
import coloredlogs
import os
from kcpr import KcprHandler
from spotify import SpotifyAuthManager
from dotenv import load_dotenv

# Load .env vars
load_dotenv()

# Spotify OAuth manager stuff
CLIENT_ID: str = os.getenv("CLIENT_ID")
CLIENT_SECRET: str = os.getenv("CLIENT_SECRET")
REDIRECT_URI: str = os.getenv("REDIRECT_URI")
SCOPES: str = os.getenv("SCOPES")
USER_ID: str = os.getenv("USER_ID")
PLAYLIST_ID: str = os.getenv("PLAYLIST_ID")


coloredlogs.install(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class KcprSpotifyScheduler():

    def __init__(self):
        self.kcpr_handler: KcprHandler = KcprHandler()
        self.spotify_handler: SpotifyAuthManager = SpotifyAuthManager(
            client_id=CLIENT_ID, client_secret=CLIENT_SECRET, redirect_uri=REDIRECT_URI, scopes=SCOPES, user_id=USER_ID)
        self.spotify_playlist_track_uris: list[str] = self.spotify_handler.get_playlist_tracks(playlist_id=PLAYLIST_ID
                                                                                               )
        self.prev_data: str = self.kcpr_handler.get_now_playing()

    def __spotify_kcpr_event(self):

        artist, song = self.kcpr_handler.get_now_playing()

        query: str = f"{artist} - {song}"

        if self.prev_data is None:
            self.prev_data = query
        # If we have new data
        if self.prev_data != query:
            # Get the track from Spotify
            logger.info(f"Now playing: {query}")
            track_uri: str = self.spotify_handler.get_track(
                artist_name=artist, title=song, similarity_threshold=0.30)

            # If the track is not in our playlist, then we'll add it.
            if not track_uri in self.spotify_playlist_track_uris:
                self.spotify_handler.add_track_to_playlist(
                    playlist_id=PLAYLIST_ID, track_id=track_uri)
                self.spotify_playlist_track_uris.append(track_uri)
                logger.info(f"Added track to playlist: {query}")

                self.prev_data = query

            else:
                logger.info(f"Track already in playlist: {query}")
        else:
            logger.info("No new data...")

    def schedule(self):
        logger.info("Scheduler started.")
        schedule.every().minute.do(self.__spotify_kcpr_event)


kcpr_scheduler: KcprSpotifyScheduler = KcprSpotifyScheduler()
kcpr_scheduler.schedule()

while True:
    schedule.run_pending()
    time.sleep(1)
