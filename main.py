import asyncio, httpx, yaml, json, eyed3

from eyed3.id3.frames import ImageFrame
from os import environ, mkdir
from vk import API

import nest_asyncio
nest_asyncio.apply()



try:
    with open("config.yml") as file:
        config = yaml.safe_load(file.read())
except FileNotFoundError:
    config = {}


def get(name, default=None):
    return config.get(name.lower()) or environ.get(name, default=default)


async def main():
    ACCESS_TOKEN = get("ACCESS_TOKEN")
    ALBUM_ID = get("ALBUM_ID")
    ALBUM_NAME = get("album_name")

    owner_id = int(ALBUM_ID.split("_")[0])
    album_id = int(ALBUM_ID.split("_")[1])

    vkapi = API(token=ACCESS_TOKEN, exec=False, v="5.131")

    res = await vkapi.request(method="audio.get", owner_id=owner_id,
                              album_id=album_id, count=120)

    artist_folder = f"music/{res['items'][0]['artist']}"

    try:
        mkdir(artist_folder)
        mkdir(f"{artist_folder}/{ALBUM_NAME}")
    except:
        pass

    for i, song in enumerate(res["items"]):
        path = f"music/{song['artist']}/{ALBUM_NAME}/{song['title']}.mp3"
        print("\x1b[2m[{}/{}]\033[0m {} — {}".format(
            i+1 if len(str(i+1)) == 2 else " " + str(i+1), len(res["items"]), song["artist"], song["title"]
        ))

        async with httpx.AsyncClient() as client:
            resp = await client.get(song["url"])

            with open(path, "wb+") as file:
                file.write(resp.read())

            audiofile = eyed3.load(path)

            if (audiofile.tag is None):
                audiofile.initTag()

            audiofile.tag.images.set(
                ImageFrame.FRONT_COVER,
                open('cover.jpg', 'rb').read(),
                'image/jpeg'
            )

            audiofile.tag.artist = song["artist"]
            audiofile.tag.album = ALBUM_NAME
            audiofile.tag.album_artist = song["artist"]
            audiofile.tag.title = song["title"]
            audiofile.tag.track_num = i + 1

            audiofile.tag.save()

    print()


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
