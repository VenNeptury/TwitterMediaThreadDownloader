import tweepy
import os
import sys
import re
import requests
import pathlib

from dotenv import load_dotenv
load_dotenv()

_img_count = 0
_already_saved_img_count = 0
_outdir = pathlib.Path.cwd()


def die(msg: str = None, code: int = 0):
    if msg:
        print(msg)
    sys.exit(code)


def downloadImages(status: tweepy.Status, outdir: pathlib.Path, individual_dir: bool):
    global _img_count
    global _already_saved_img_count

    images = [x["media_url"] for x in status.extended_entities["media"]]

    final_dir = outdir

    if individual_dir:
        final_dir /= status.id_str

        try:
            final_dir.mkdir()
        except FileExistsError:
            file_count = len(list(final_dir.glob("*")))
            if file_count == len(images):
                _already_saved_img_count += file_count
                print(f"Tweet already downloaded. Skipping...")
                return
            pass

    for i, img in enumerate(images):
        res = requests.get(img)

        file_name = f"{i+1}{os.path.splitext(img)[1]}"

        if not individual_dir:
            file_name = status.id_str + file_name

        final_path = final_dir / file_name
        if final_path.exists():
            _already_saved_img_count += 1
            continue

        with open(final_path, "w+b") as f:
            f.write(res.content)
            _img_count += 1


def main():
    global _outdir

    if len(sys.argv) == 1:
        die(f"Usage: {sys.argv[0]} <Last Tweet in Thread> [outdir] [whether to create separate dir for each tweet]")

    tweet_id = re.match(
        "https://twitter.com/\w+/status/(\d+)", sys.argv[1])

    if not tweet_id:
        die("That doesn't seem to be a valid tweet. Please try again!")
    else:
        tweet_id = tweet_id.group(1)

    if len(sys.argv) >= 3:
        custom_path = pathlib.Path(sys.argv[2])
        _outdir = custom_path if custom_path.is_absolute else _outdir / custom_path
    else:
        _outdir /= tweet_id

    try:
        _outdir.mkdir(exist_ok=True)
    except Exception as e:
        die(f"Something went wrong while creating the directory: {e}")

    individual_dir = len(sys.argv) > 3 and sys.argv[3].lower() in [
        "y", "yes", "true", "1"]
    tweet_count = 0

    auth = tweepy.OAuthHandler(
        os.getenv("TWITTER_CONSUMER_KEY"), os.getenv("TWITTER_CONSUMER_SECRET"))
    auth.set_access_token(
        os.getenv("TWITTER_ACCESS_TOKEN"), os.getenv("TWITTER_ACCESS_SECRET"))

    session = tweepy.API(auth)

    if not session.verify_credentials():
        die("Twitter API authentication failed. Make sure you renamed the .env.example file to .env and filled it with the appropriate api tokens.")

    last_tweet = None

    try:
        last_tweet = session.get_status(tweet_id)
    except tweepy.error.TweepError:
        die("I wasn't able to fetch that tweet. Please try again!")
    except Exception:
        die("An unknown error occurred. Please try again!")

    input(
        f"Saving all media of thread by {last_tweet.user.screen_name} to {_outdir.absolute()}. {'Creating individual subdir for each tweet. ' if individual_dir else ''}Press any key to proceed... ")

    while 1:
        tweet_count += 1

        if not last_tweet.extended_entities:
            print("Found tweet with no media. Skipping...")
        else:
            print(
                f"Found tweet with {len(last_tweet.extended_entities['media'])} images. Downloading...")
            try:
                downloadImages(last_tweet, _outdir, individual_dir)
            except Exception as e:
                print(f"Something went wrong. Carrying on... (Error: {e})")

        if not last_tweet.in_reply_to_status_id:
            break

        last_tweet = session.get_status(last_tweet.in_reply_to_status_id)

    print(
        f"Finished downloading. Handled {tweet_count} tweets and downloaded {_img_count} images.")
    if _already_saved_img_count:
        print(
            f"Skipped {_already_saved_img_count} images because they were already downloaded.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        if not _outdir or _outdir == pathlib.Path.cwd():
            die(None, 130)

        delete_dir = input("\n\nExiting... Delete Download Directory? [y|N]...\n> ") in [
            "y", "yes", "true"]
        if delete_dir:
            from shutil import rmtree
            rmtree(_outdir)

        die(None, 130)
