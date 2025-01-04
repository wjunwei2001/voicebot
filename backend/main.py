from fastapi import FastAPI, UploadFile, HTTPException
from pydantic import BaseModel
import openai
import uvicorn
import tempfile
import os
from audio_processing import transcribe_audio
from dotenv import load_dotenv

# Initialize FastAPI app
app = FastAPI()

load_dotenv()

# Set your OpenAI API key
openai.api_key = os.environ.get("OPENAI_KEY")

class ChatRequest(BaseModel):
    text: str

@app.post("/chat/")
async def chat_with_openai(request: ChatRequest):
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": request.text}]
        )
        chatbot_reply = response.choices[0].message.content
        return {"response": chatbot_reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/audio-to-text/")
async def audio_to_text(filepath):
    try:
        # Save uploaded file temporarily
        # with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
        #     temp_file.write(await file.read())
        #     temp_path = temp_file.name

        # Convert audio to text
        transcribed_text = transcribe_audio(filepath)
        os.remove(filepath)  # Clean up the temporary file
        return {"text": transcribed_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)