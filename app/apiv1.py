from fastapi import FastAPI, File, UploadFile , HTTPException ,Body
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import Resona
import shutil
import os
import sqlite3
import yt_dlp
from pydantic import BaseModel

class Song(BaseModel):
    songname: str

app = FastAPI()

# ✅ Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/audio")
async def recognize(file: UploadFile = File(...)):
    temp_path = f"temp_{file.filename}"
    try:
        # Save uploaded file to disk
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Run recognition
        song, score = Resona.recognize(temp_path)
        print("Predicted:", song, "Score:", score)

        # Explicit JSON response
        return JSONResponse(
            content={
                "filename": file.filename,
                "predicted_song": song,
                "score": score
            }
        )
    finally:
        # print("bye")
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.get("/getsongs")
def listsongs():
    conn = sqlite3.connect("./fingerprints.db")
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM songs;")
        rows = c.fetchall()   
        c.close
        return JSONResponse(rows)
    except Exception as e:
        print(f"Error fetching songs: {e}")
        return []
    

@app.post("/addsong")
async def addsong(file: UploadFile = File(...)):
    directory_path = "../songs"
    full_path = os.path.join(directory_path, file.filename)

    try:
        with open(full_path, mode="wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        Resona.add_song(full_path)

        return JSONResponse("Song addedd :{file.filename}")
    
    except Exception as e:
        return JSONResponse(f"Error on server side {e}")



@app.delete("/deletesong")
async def delete_song(filename: str = Body(..., embed=True, alias="filename")):
   
    directory_path = "../songs"
    full_path = os.path.join(directory_path, filename)

    conn = None 
    
    try:
        # --- File Deletion ---
        if os.path.exists(full_path):
            os.remove(full_path)
            print(f"File deleted: {full_path}")
        else:
            print(f"File not found on disk: {full_path}. Checking database...")


        # --- Database Deletion ---
        conn = sqlite3.connect("./fingerprints.db")
        c = conn.cursor()
        
        # Step A: Find the song's ID using the filename (which is stored in the 'name' column)
        c.execute("SELECT id FROM songs WHERE name = ?", (filename,))
        row = c.fetchone()
        
        if row:
            song_id = row[0]
            
            # Step B: Delete the song's entry from the 'songs' table
            c.execute("DELETE FROM songs WHERE id = ?", (song_id,))
            
            # Step C: Delete all associated fingerprints from the 'fingerprints' table
            c.execute("DELETE FROM fingerprints WHERE song_id = ?", (song_id,))
            
            conn.commit()
            
            return JSONResponse(
                content={"message": f"Successfully deleted song '{filename}' (ID: {song_id}) from disk and database."}
            )
        else:
            # If the entry was not found in the DB
            return JSONResponse(
                status_code=200,
                content={"message": f"File deletion complete. Database entry for '{filename}' was already missing."}
            )

    except Exception as e:
        if conn:
            conn.rollback()
        
        print(f"Error during song deletion: {e}")
        # Raise an HTTPException for proper FastAPI error response
        raise HTTPException(
            status_code=500, 
            detail=f"An error occurred on the server side: {e}"
        )
        
    finally:
        
        if conn:
            conn.close()


@app.post("/addytsongs")
async def addfromyt(payload : Song):
    song =  payload.songname

    try:
        ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': '../songs/%(title)s.%(ext)s',
        
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            query = f"ytsearch1:{song}"
            print(f"Downloading: {song} by {song}")
            ydl.download([query])

            info_result = ydl.extract_info(query, download=False)

            video_info = info_result['entries'][0]

            temp_filename_with_wrong_ext = ydl.prepare_filename(video_info) 

            base_name, _ = os.path.splitext(temp_filename_with_wrong_ext)
            full_path_for_resona = base_name + ".mp3"

            Resona.add_song(full_path_for_resona)
    


        return JSONResponse(f"Succesfully added song ({song})  from YT {full_path_for_resona} ")    
    except Exception as e:
        return JSONResponse(f"Error in serverside {e} ")


    