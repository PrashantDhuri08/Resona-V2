import os
import Resona


def main():
    song_files = [os.path.join(Resona.SONG_FOLDER, f) for f in os.listdir(Resona.SONG_FOLDER)
                  if f.lower().endswith((".mp3", ".wav", ".flac", ".ogg", ".m4a"))]

    # assign numeric IDs
    for idx, path in enumerate(song_files, start=1):
        Resona.add_song(idx, path)

    query = "query.wav"  # realtime audio clip recorded from mic
    # query = "../sumc.mp3"  (audio clip cropped from songs)
    song, score = Resona.recognize(query)
    print("Predicted:", song, "Score:", score)


main()
