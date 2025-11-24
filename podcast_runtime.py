#!/usr/bin/env python3
"""Fetch duration (in ms) of all episodes for a Spotify podcast."""

import csv
import json
import os
import re
import sys
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from getpass import getpass
from typing import Any, TextIO
from urllib import request
from urllib.parse import urlencode, urljoin

# Python 3.7+: if redirecting on Windows to '> $null' in e.g. PowerShell, it
# will fall back to system default encoding (usually cp1252) which may fail if a
# podcast has characters that this encoding can't handle.
sys.stdout.reconfigure(encoding="utf-8")  # pyright: ignore[reportGeneralTypeIssues]
sys.stderr.reconfigure(encoding="utf-8")  # pyright: ignore[reportGeneralTypeIssues]

SHOWS_URL = "https://api.spotify.com/v1/shows/"
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")


def get_access_token() -> str:
    """Request an API access token (good for 1 hour)."""
    client_id = CLIENT_ID or getpass("Spotify client ID: ")
    client_secret = CLIENT_SECRET or getpass("Spotify client secret: ")

    params = urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )

    req = request.Request(
        url=f"https://accounts.spotify.com/api/token?{params}",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )

    with request.urlopen(req) as resp:
        body = resp.read()
        token_info = json.loads(body.decode())
        access_token = token_info["access_token"]

    return access_token


def _get(url: str, token: str) -> dict[str, Any]:
    """Send a simple GET request and decode the JSON response."""
    req = request.Request(url=url, headers={"Authorization": f"Bearer {token}"})

    with request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())

    return data


def _get_podcast_name(podcast_id: str, token: str) -> str:
    """Fetch a podcast's advertised name."""
    show_url = urljoin(SHOWS_URL, f"{podcast_id}")
    data = _get(url=show_url, token=token)
    return data["name"]


def _parse_id(url_or_id: str) -> str:
    """If given a spotify URL, extract the podcast ID."""
    if m := re.match(r"https?://[^/]+/show/([a-zA-Z0-9]+)", url_or_id):
        (podcast_id,) = m.groups(1)
        return str(podcast_id)

    return str(url_or_id)


class DataWriter:
    """Export lines read from Spotify to stdout or a file."""

    def __init__(
        self,
        episodes_url: str,
        out: str | bytes | os.PathLike | TextIO,
        token: str,
        limit: int | None = None,
    ) -> None:
        self.token = token
        self.write_mode = "w"
        self.episode_count = 1
        self.total_duration_ms = 0.0
        self.out = out
        self.limit = limit
        self.episodes_url = episodes_url

    @property
    def duration_seconds(self) -> int:
        """Total runtime of podcast in seconds."""
        return int(self.total_duration_ms // 1000)

    @property
    def duration_hours(self) -> int:
        """Total runtime of podcast in hours (rounded down)."""
        return self.duration_seconds // 3600

    @property
    def duration_minutes(self) -> int:
        """When using `duration_hours`, this is the remainder in minutes."""
        return int((self.duration_seconds % 3600) // 60)

    def _write_batch(self, data: dict[str, Any]) -> None:
        """Write episode data to either a file or stdout."""
        f = self.out

        try:
            if self.out is not sys.stdout:
                assert not isinstance(self.out, TextIO)  # noqa: S101
                f = open(  # noqa: SIM115, PTH123
                    self.out,
                    mode=self.write_mode,
                    encoding="utf-8",
                )

            writer = csv.DictWriter(
                f,  # pyright: ignore[reportGeneralTypeIssues]
                fieldnames=["number", "name", "runtime_ms"],
            )

            if self.write_mode == "w":
                writer.writeheader()
            for episode in data.get("items", []):
                if episode is None:
                    continue
                duration = float(episode.get("duration_ms", 0))
                writer.writerow(
                    {
                        "number": self.episode_count,
                        "name": episode.get("name", ""),
                        "runtime_ms": duration,
                    },
                )
                self.episode_count += 1
                self.total_duration_ms += duration
                self.write_mode = "a"
                self.episodes_url = data.get("next")
        finally:
            if f is not sys.stdout:
                try:
                    f.close()  # pyright: ignore[reportGeneralTypeIssues]
                finally:
                    pass

    def write(self) -> None:
        """Query and write episode data."""
        while self.episodes_url:
            data = _get(url=self.episodes_url, token=self.token)
            _ = self._write_batch(data=data)
            if self.limit and self.episode_count >= self.limit:
                break


def main(
    podcast_id: str,
    out: str | TextIO | None = None,
    page_size: int = 50,
    limit: int | None = None,
) -> None:
    """Query Spotify API for a podcast's episode information and write to `out`."""
    token = get_access_token()

    if out is None:
        name = _get_podcast_name(podcast_id=podcast_id, token=token)
        ascii_only_name = re.sub(r"[^\x00-\x7F]+", "_", name)
        out = f"{ascii_only_name}.csv"

    writer = DataWriter(
        episodes_url=urljoin(SHOWS_URL, f"{podcast_id}/episodes?limit={page_size}"),
        out=out,
        token=token,
        limit=limit,
    )

    writer.write()

    sys.stderr.write(
        f"{writer.episode_count} episodes, "
        f"totaling {int(writer.duration_hours)} hours, "
        f"{int(writer.duration_minutes)} minutes\n",
    )

    if out is not sys.stdout:
        sys.stderr.write(f"written to {out}")


if __name__ == "__main__":
    parser = ArgumentParser(
        description=__doc__,
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    _ = parser.add_argument(
        "PODCAST_URL_OR_ID",
        help="URL or ID of the podcast to query (accepts URLs from the 'share' menu in Spotify)",
    )
    _ = parser.add_argument(
        "--out",
        "-o",
        default=None,
        type=str,
        help=(
            "File name to save results to. "
            "If not provided and --stdio is not set, will use the podcast's title."
        ),
    )
    _ = parser.add_argument(
        "--limit",
        "-l",
        default=None,
        required=False,
        type=int,
        help="Max number of lines to write (+/- batch size)",
    )
    _ = parser.add_argument(
        "--pagesize",
        "-p",
        default=50,
        type=int,
        help="Batch size; number of episodes to pull per request",
    )
    _ = parser.add_argument(
        "--stdout",
        action="store_true",
        help="If provided, write to stdout instead of a file",
    )

    args = parser.parse_args()
    out: TextIO | str | None = sys.stdout if args.stdout else args.out
    podcast_id: str = _parse_id(args.PODCAST_URL_OR_ID)
    page_size: int = args.pagesize
    limit: int = args.limit

    main(podcast_id=podcast_id, out=out, page_size=page_size, limit=limit)
