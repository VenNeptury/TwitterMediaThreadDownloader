import typing
import os
import sys
import re
import requests
import pathlib
import json
import time


def die(msg: str = None, code: int = 0):
    if msg:
        print(msg)
    sys.exit(code)


class TwitterThreadDownloader:
    _API_BASE = 'https://api.twitter.com/1.1/'
    _GUEST_TOKEN = None
    _COUNTS = {
        "tweets": 0,
        "images_saved": 0,
        "already_saved": 0,
    }
    _OPTIONS = {
        "tweet_id": None,
        "outdir": pathlib.Path.cwd(),
        "individual_dirs": False,
        "authorization": 'Bearer AAAAAAAAAAAAAAAAAAAAAPYXBAAAAAAACLXUNDekMxqa8h%2F40K4moUkGsoc%3DTYfbDKbT3jJPCEVnMYqilB28NHfOPqkca3qaAxGfsyKCs0wRbw'
    }
    _CURSOR = None

    def __init__(self, argv: typing.List[str]):
        if len(sys.argv) == 1:
            die(f"Usage: {argv[0]} <Last Tweet in Thread> [outdir] [whether to create separate dir for each tweet]")

        tweet_id = re.match(
            "https://twitter.com/\w+/status/(\d+)", argv[1])

        if tweet_id is None:
            die("That doesn't seem to be a valid tweet. Please try again!")
        else:
            tweet_id = self._OPTIONS['tweet_id'] = tweet_id.group(1)

        if len(sys.argv) >= 3:
            custom_path = pathlib.Path(sys.argv[2])
            self._OPTIONS["outdir"] = custom_path if custom_path.is_absolute else self._OPTIONS["outdir"] / custom_path
        else:
            self._OPTIONS["outdir"] /= tweet_id

        try:
            self._OPTIONS['outdir'].mkdir(exist_ok=True)
        except Exception as e:
            die(f'Something went wrong while creating the directory: {e}')

        self._OPTIONS['individual_dirs'] = len(argv) > 3 and argv[3].lower() in [
            "y", "yes", "true", "1"]

    def request_json(self, endpoint: str, method: str = "get", **kwargs):
        res = None
        try:
            fetch_method = requests.get if method.lower() != "post" else requests.post
            res = fetch_method(self._API_BASE + endpoint, **kwargs)
            return json.loads(res.content)
        except json.JSONDecodeError as err:
            print(
                f'An error occurred while parsing json from {endpoint} -> {err}\n\nRaw json: {res.content if res else "-"}')
        except requests.exceptions.RequestException as err:
            print(f"An error occurred while fetching {endpoint} -> {err}")

    def get_tweet(self, tweet_id: str):
        headers = {
            'Authorization': self._OPTIONS["authorization"],
        }

        if self._GUEST_TOKEN is None:
            res = self.request_json(
                'guest/activate.json', "post", headers=headers)
            self._GUEST_TOKEN = res['guest_token']

        headers['x-guest-token'] = self._GUEST_TOKEN
        return self.request_json(f'statuses/show.json?id={tweet_id}', headers=headers)

    def download_media(self, status):
        images = [x["media_url"] for x in status['extended_entities']['media']]

        final_dir = self._OPTIONS["outdir"]
        individual_mode = self._OPTIONS['individual_dirs']
        count = 0
        dir_name = None

        try:
            dir_name = re.sub('[^A-Za-z0-9]|https://t.co/\w+',
                              "", status['text'])[: 30]
            if not len(dir_name):
                raise Exception
        except:
            dir_name = status['id_str']
            pass

        if individual_mode:
            final_dir /= dir_name

            try:
                final_dir.mkdir()
            except FileExistsError:
                file_count = len(list(final_dir.glob("*")))
                if file_count == len(images):
                    self._COUNTS["already_saved"] += file_count
                    print(f"Tweet already downloaded. Skipping...")
                    return 0
                pass

        for i, img in enumerate(images):
            file_ext = os.path.splitext(img)[1]
            file_name = f'{i+1}{file_ext}'

            if not individual_mode:
                file_name = dir_name + "-" + file_name

            final_path = final_dir / file_name
            if final_path.exists():
                self._COUNTS["already_saved"] += 1
                continue

            res = requests.get(img)

            with open(final_path, "w+b") as f:
                f.write(res.content)
                count += 1

        self._COUNTS["images_saved"] += count

        return count

    def download(self):
        cursor = self._CURSOR = self.get_tweet(self._OPTIONS['tweet_id'])
        if cursor is None:
            die()

        input(f'Saving all media of thread by {cursor["user"]["screen_name"]} to {self._OPTIONS["outdir"].absolute()}.\n' +
              ("Creating individual subdir for each tweet. " if self._OPTIONS[
                  "individual_dirs"] else "") +
              'Press any key to proceed...')

        chunk = 0
        while 1:
            self._COUNTS["tweets"] += 1
            chunk += 1

            tweet_url = f'https://twitter.com/i/status/{cursor["id_str"]}'
            if 'extended_entities' not in cursor or not cursor['extended_entities']:
                print(f"Found tweet {tweet_url} with no media. Skipping...")
            else:
                print(
                    f'Found tweet {tweet_url} with {len(cursor["extended_entities"]["media"])} images. Downloading...')
                try:
                    self.download_media(cursor)
                except Exception as e:
                    print(f"Something went wrong. Carrying on... (Error: {e})")

            if not 'in_reply_to_status_id' in cursor or not cursor['in_reply_to_status_id']:
                break

            if chunk == 10:
                print(f"Finished fetching 10 tweets. Pausing for a bit...")
                time.sleep(5)
                chunk = 0
            cursor = self.get_tweet(cursor['in_reply_to_status_id'])

        print((
            'Finished downloading.'
            f'Handled {self._COUNTS["tweets"]} tweets and downloaded {self._COUNTS["images_saved"]} images'
        ))
        if self._COUNTS["already_saved"]:
            print(
                f'Skipped {self._COUNTS["already_saved"]} images because they were already downloaded.')

    def cleanup(self):
        from shutil import rmtree
        rmtree(self._OPTIONS['outdir'])


if __name__ == "__main__":
    threader = TwitterThreadDownloader(sys.argv)
    try:
        threader.download()
    except KeyboardInterrupt:
        if threader._OPTIONS['outdir'] == pathlib.Path.cwd():
            die(None, 130)

        delete_dir = input("\n\nExiting... Delete Download Directory? [y|N]...\n> ") in [
            "y", "yes", "true"]
        if delete_dir:
            threader.cleanup()

        die(None, 130)
