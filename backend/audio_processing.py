import whisper  

def transcribe_audio(audio_path):
    model = whisper.load_model("base")
    result = model.transcribe(audio=audio_path, verbose=True)
    print(result)
    return result['text']
