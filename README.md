# Spotify podcast stats

Fetch episodes and their runtime from the Spotify API.  Requires Python 3 with
no other dependencies.

## Usage

Download the `podcast_runtime.py` and run it with Python.  Depending on your
installation it may be a slightly different command but usually it's
`python3 podcast_runtime.py`.
It uses only the Python3 standard library, so there is no need to install
anything with pip.  I wrote and tested it with Python 3.14, so I recommend using
at least that version, but it may work on older Python versions.

```
$ .\podcast_runtime.py https://open.spotify.com/show/6EqvqiiuZnCY9YVYmKAojD?si=668e772a777840bf
701 episodes, totaling 188 hours, 51 minutes
written to Nihongo con Teppei Original Archives 1-700.csv
```

For all options, use `--help`:

```
$ python3 .\podcast_runtime.py --help
usage: podcast_runtime.py [-h] [--out OUT] [--limit LIMIT] [--pagesize PAGESIZE] [--stdout] PODCAST_URL_OR_ID

Fetch duration (in ms) of all episodes for a Spotify podcast.

positional arguments:
  PODCAST_URL_OR_ID     URL or ID of the podcast to query (accepts URLs from the 'share' menu in Spotify)

options:
  -h, --help            show this help message and exit
  --out, -o OUT         File name to save results to. If not provided and --stdio is not set, will use the
                        podcast's title. (default: None)
  --limit, -l LIMIT     Max number of lines to write (+/- batch size) (default: None)
  --pagesize, -p PAGESIZE
                        Batch size; number of episodes to pull per request (default: 50)
  --stdout              If provided, write to stdout instead of a file (default: False)
```
