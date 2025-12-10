import librosa
import numpy as np
import sqlite3
import hashlib
import os
from collections import defaultdict, Counter
from scipy.ndimage import maximum_filter


SR = 22050
N_FFT = 1024    
HOP = 512
FAN_VALUE = 5    
AMP_MIN = -40
TARGET_WINDOW = 100
SONG_FOLDER = "../songs"
DB_PATH = "fingerprints.db"

# SONG_FOLDER = "./spotify/songs"
# DB_PATH = "./spotify/fingerprints.db"

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS fingerprints (
    hash INTEGER,
    song_id INTEGER,
    time INTEGER
);""")

c.execute("""CREATE TABLE IF NOT EXISTS songs (
    id INTEGER PRIMARY KEY,
    name TEXT
);
""")

c.execute("CREATE INDEX IF NOT EXISTS idx_hash ON fingerprints(hash);")

conn.commit()


def get_spectrogram(path):
    y, sr = librosa.load(path, sr=SR)
    if np.max(np.abs(y)) > 0:
        y = y / np.max(np.abs(y))
    S = np.abs(librosa.stft(y, n_fft=N_FFT, hop_length=HOP))
    S_db = librosa.amplitude_to_db(S, ref=np.max)
    return S_db


def get_peaks(S_db):
    local_max = maximum_filter(S_db, footprint=np.ones((7, 7))) == S_db
    detected = local_max & (S_db > AMP_MIN)
    peaks = np.argwhere(detected)
    return peaks[np.argsort(peaks[:, 1])]


def generate_hashes(peaks):
    for i in range(len(peaks)):
        freq1, t1 = peaks[i]
        for j in range(1, FAN_VALUE):
            if i + j < len(peaks):
                freq2, t2 = peaks[i + j]
                dt = t2 - t1
                if 0 < dt <= TARGET_WINDOW:
                    raw = f"{freq1}|{freq2}|{dt}"
                    h = int(hashlib.sha1(raw.encode()).hexdigest()[:10], 16)
                    yield h, int(t1)




# def add_song(song_id, path):

def add_song(path):
    name = os.path.basename(path)

    # check if this song (by name) is already in DB
    c.execute("SELECT id FROM songs WHERE name=?", (name,))
    row = c.fetchone()
    if row:
        print(f"Skipping {name}, already indexed (id={row[0]}).")
        return

    # insert new song row, get its id
    c.execute("INSERT INTO songs(name) VALUES (?)", (name,))
    song_id = c.lastrowid

    # fingerprint
    S_db = get_spectrogram(path)
    peaks = get_peaks(S_db)

    rows = []
    for h, t in generate_hashes(peaks):
        rows.append((h, song_id, t))

    c.executemany(
        "INSERT INTO fingerprints(hash, song_id, time) VALUES (?,?,?)",
        rows,
    )
    conn.commit()

    print(f"Indexed {name}: {len(rows)} hashes (id={song_id})")

    name = os.path.basename(path)
    # skip if already indexed
    c.execute("SELECT 1 FROM songs WHERE id=?", (song_id,))
    if c.fetchone():
        print(f"Skipping {name}, already indexed.")
        return
    c.execute("INSERT INTO songs(id, name) VALUES (?,?)", (song_id, name))
    S_db = get_spectrogram(path)
    peaks = get_peaks(S_db)

    rows = []
    for h, t in generate_hashes(peaks):
        rows.append((h, song_id, t))

    c.executemany("INSERT INTO fingerprints(hash, song_id, time) VALUES (?,?,?)", rows)
    conn.commit()

    print(f"Indexed {os.path.basename(path)}: {len(rows)} hashes")

def recognize(path):
    S_db = get_spectrogram(path)
    peaks = get_peaks(S_db)

    matches = defaultdict(list)

    for h, t in generate_hashes(peaks):
        c.execute("SELECT song_id, time FROM fingerprints WHERE hash=?", (h,))
        for song_id, db_time in c.fetchall():
            matches[song_id].append(db_time - t)

    if not matches:
        return None, 0

    best_song, best_score = None, 0

    for song_id, deltas in matches.items():
        if not deltas:
            continue
        cluster = Counter(deltas).most_common(1)[0][1]
        if cluster > best_score:
            best_score = cluster
            best_song = song_id

    # fetch name
    c.execute("SELECT name FROM songs WHERE id=?", (best_song,))
    row = c.fetchone()
    return (row[0] if row else best_song), best_score


