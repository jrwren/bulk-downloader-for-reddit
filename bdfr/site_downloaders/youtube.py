#!/usr/bin/env python3

import logging
import tempfile
from pathlib import Path
from typing import Callable, Optional

import yt_dlp
from praw.models import Submission

from bdfr.exceptions import NotADownloadableLinkError, SiteDownloaderError
from bdfr.resource import Resource
from bdfr.site_authenticator import SiteAuthenticator
from bdfr.site_downloaders.base_downloader import BaseDownloader

logger = logging.getLogger(__name__)


class Youtube(BaseDownloader):
    def __init__(self, post: Submission):
        super().__init__(post)

    def find_resources(self, authenticator: Optional[SiteAuthenticator] = None) -> list[Resource]:
        ytdl_options = {
            'format': 'best',
            'playlistend': 1,
            'nooverwrites': True,
        }
        download_function = self._download_video(ytdl_options)
        try:
            extension = self.get_video_attributes(self.post.url)['ext']
        except KeyError:
            raise NotADownloadableLinkError(f'Youtube-DL cannot download URL {self.post.url}')
        res = Resource(self.post, self.post.url, download_function, extension)
        return [res]

    def _download_video(self, ytdl_options: dict) -> Callable:
        yt_logger = logging.getLogger('youtube-dl')
        yt_logger.setLevel(logging.CRITICAL)
        ytdl_options['quiet'] = True
        ytdl_options['logger'] = yt_logger

        def download(_: dict) -> bytes:
            with tempfile.TemporaryDirectory() as temp_dir:
                download_path = Path(temp_dir).resolve()
                ytdl_options['outtmpl'] = str(download_path) + '/' + 'test.%(ext)s'
                try:
                    with yt_dlp.YoutubeDL(ytdl_options) as ydl:
                        ydl.download([self.post.url])
                except yt_dlp.DownloadError as e:
                    raise SiteDownloaderError(f'Youtube download failed: {e}')

                downloaded_files = list(download_path.iterdir())
                if len(downloaded_files) > 0:
                    downloaded_file = downloaded_files[0]
                else:
                    raise NotADownloadableLinkError(f"No media exists in the URL {self.post.url}")
                with open(downloaded_file, 'rb') as file:
                    content = file.read()
                return content
        return download

    @staticmethod
    def get_video_attributes(url: str) -> dict:
        yt_logger = logging.getLogger('youtube-dl')
        yt_logger.setLevel(logging.CRITICAL)
        with yt_dlp.YoutubeDL({'logger': yt_logger, }) as ydl:
            try:
                result = ydl.extract_info(url, download=False)
                return result
            except Exception as e:
                logger.exception(e)
