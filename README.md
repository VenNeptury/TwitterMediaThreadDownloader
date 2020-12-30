# Twitter Thread Media Downloader

Tool to download all images from a Twitter Thread

## Usage

Rename the file `.env.example` to `.env` and fill it out with your twitter api tokens.

Now run the following commands

```bash
pip install -r requirements.txt

# Do not include the <> and [] in your command, they indicate mandatory (<>) and optional ([]) arguments.
python threader.py <link to tweet> [outdir (defaults to using the tweet ID as dirname)] [whether to create individual subfolders per tweet (y|n)]
```

Due to twitter api limitations, you must provide the last tweet in the thread instead of the first.
