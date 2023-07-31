from os import environ
import tempfile
from urllib.parse import urlparse

from faster_whisper import WhisperModel
import nio
import simplematrixbotlib as botlib

creds = botlib.Creds(environ.get("SERVER_URL"), environ.get("USERNAME"), environ.get("PASSWORD"))
config = botlib.Config()
config.timeout = 180000
bot = botlib.Bot(creds, config)

def transcribe(data):
    model_path = "models/whisper-small-ct2/"

    # Run on CPU with INT8
    model = WhisperModel(model_path, device="cpu", compute_type="int8")

    # or run on GPU with FP16
    # model = WhisperModel(model_size, device="cuda", compute_type="float16")
    # or run on GPU with INT8
    # model = WhisperModel(model_path, device="cuda", compute_type="int8_float16")

    segments, info = model.transcribe(data, beam_size=5)

    print("Detected language '%s' with probability %f" % (info.language, info.language_probability))

    # for segment in segments:
    #     print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))

    return segments

async def handle_audio_message(room, event, encrypted):
    if encrypted:
        print("Got encrypted audio event")
    else:
        print("Got unencrypted audio event")

    if "Voice message" not in event.body:
        print("Skipping because no voice message")

    await bot.async_client.room_typing(room.room_id, typing_state=True)

    url = urlparse(event.url)
    response = await bot.async_client.download(server_name=url.netloc, media_id=url.path.strip("/"))

    if isinstance(response, nio.responses.DownloadError):
        print("Error downloading file")
    else:
        f = tempfile.NamedTemporaryFile("w+b", delete=False)

        if encrypted:
            decrypted_data = nio.crypto.decrypt_attachment(
                response.body,
                event.key["k"], 
                event.hashes["sha256"],
                event.iv)

            f.write(decrypted_data)
        else:
            f.write(response.body)

        f.close()

        print(f"File {event.url} downloaded and decrypted, transcribing..")

        segments = transcribe(f.name)

        print("Successfully transcribed, sending message..")

        await bot.api.send_markdown_message(
            room.room_id, ("**ɔ** " + " ".join(segment.text.strip() for segment in segments)).strip()
            )

        print("Sent")

    await bot.async_client.room_typing(room.room_id, typing_state=False)

@bot.listener.on_custom_event(nio.RoomMessageAudio)
async def handle_unencrypted_media(room, event):
    return await handle_audio_message(room, event, encrypted=False)

@bot.listener.on_custom_event(nio.RoomEncryptedAudio)
async def handle_encrypted_audio(room, event):
    return await handle_audio_message(room, event, encrypted=True)

bot.run()
