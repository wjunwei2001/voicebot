import streamlit as st
import requests 
import os
import uuid
from streamlit_chat import message
import sounddevice as sd
import wavio
import numpy as np
import tempfile
from datetime import datetime
import queue
import time
import threading

# Backend URLs
AUDIO_TO_TEXT_URL = "http://localhost:8000/audio-to-text/"
CHAT_URL = "http://localhost:8000/chat/"

# Audio recording parameters
SAMPLE_RATE = 44100
CHANNELS = 2

def init_state():
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "recording_state" not in st.session_state:
        st.session_state.recording_state = "stopped"
    if "audio_data" not in st.session_state:
        st.session_state.audio_data = []
    if "audio_recorder" not in st.session_state:
        st.session_state.audio_recorder = None

class AudioRecorder:
    def __init__(self):
        self.audio_data = []
        self.is_recording = False
        self._queue = queue.Queue()

    def callback(self, indata, frames, time, status):
        if status:
            print(status)
        self._queue.put(indata.copy())

    def start(self):
        self.audio_data = []
        self.is_recording = True
        self.stream = sd.InputStream(
            channels=CHANNELS,
            samplerate=SAMPLE_RATE,
            callback=self.callback
        )
        self.stream.start()

        # Start a thread to collect audio data
        def collect_audio():
            while self.is_recording:
                try:
                    self.audio_data.append(self._queue.get(timeout=0.5))
                except queue.Empty:
                    continue

        self.collect_thread = threading.Thread(target=collect_audio)
        self.collect_thread.start()

    def stop(self):
        self.is_recording = False
        if hasattr(self, 'collect_thread'):
            self.collect_thread.join()
        if hasattr(self, 'stream'):
            self.stream.stop()
            self.stream.close()
        return self.audio_data

def save_audio(audio_data, sample_rate=SAMPLE_RATE):
    """Save the recorded audio to a temporary WAV file"""
    if not audio_data:
        return None
        
    temp_dir = tempfile.gettempdir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(temp_dir, f"recording_{timestamp}.wav")
    
    try:
        # Convert list of blocks to a single numpy array
        audio_array = np.concatenate(audio_data, axis=0)
        
        # Normalize audio data
        audio_array = audio_array / np.max(np.abs(audio_array))
        
        # Save as WAV file
        wavio.write(filename, audio_array, sample_rate, sampwidth=3)
        return filename
    except Exception as e:
        st.error(f"Error saving audio: {str(e)}")
        return None

def process_audio_to_chat(audio_file_path):
    """Process audio file and send to chat"""
    try:
        # Send audio file for transcription
        with open(audio_file_path, 'rb') as audio_file:
            files = {"file": audio_file}
            response = requests.post(AUDIO_TO_TEXT_URL, files=files)
            transcribed_text = response.json().get("text", "")

        if transcribed_text:
            # Send transcribed text to chat
            response = requests.post(CHAT_URL, json={"text": transcribed_text})
            return transcribed_text, response.json().get("response", "")
        return None, "Could not transcribe audio"
    except Exception as e:
        return None, f"Error processing audio: {str(e)}"

# Streamlit layout
st.set_page_config(page_title="Voice & Chat Chatbot", layout="wide")
st.title("🎙️ Voice & Chat Chatbot")

# Initialize session state
init_state()

# Tabs for Chat and Voice
tabs = st.tabs(["💬 Chat Interface", "🎤 Voice Input"])

# Chat Interface Tab
with tabs[0]:
    st.subheader("💬 Chat Interface")

    # Initialize session state for chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
        st.session_state.recording = False
    
    with st.sidebar:
        if st.button("Reset Session"):
            init_state()

    # Messages in the conversation
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"], unsafe_allow_html=True)

    # Chat input that invokes the agent
    if prompt := st.chat_input():
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("...")
            try:
                response = requests.post(CHAT_URL, json={"text": prompt})
                bot_response = response.json().get("response", "Error retrieving response.")
            except Exception as e:
                bot_response = "Error connecting to the chatbot server."
            output_text = bot_response

            placeholder.markdown(output_text, unsafe_allow_html=True)
            st.session_state.messages.append({"role": "assistant", "content": output_text})

# Voice Input Tab
with tabs[1]:
    st.subheader("🎤 Voice Input")

    col1, col2 = st.columns(2)
    
    with col1:
        st.write("📝 Live Recording")
        
        # Recording controls
        if st.session_state.recording_state == "stopped":
            if st.button("Start Recording"):
                st.session_state.recording_state = "recording"
                st.session_state.audio_recorder = AudioRecorder()
                st.session_state.audio_recorder.start()
                
        elif st.session_state.recording_state == "recording":
            st.warning("🔴 Recording in progress...")
            if st.button("Stop Recording"):
                if st.session_state.audio_recorder:
                    audio_data = st.session_state.audio_recorder.stop()
                    if audio_data:
                        st.session_state.audio_data = audio_data
                        st.session_state.recording_state = "processing"
                    else:
                        st.session_state.recording_state = "stopped"
                        st.error("No audio data recorded")
                
        elif st.session_state.recording_state == "processing":
            with st.spinner("Processing audio..."):
                audio_file_path = save_audio(st.session_state.audio_data)
                print("Audio file path: ", audio_file_path)
                if audio_file_path:
                    transcribed_text, bot_response = process_audio_to_chat(audio_file_path)
                    print(transcribed_text, bot_response)
                    if transcribed_text:
                        st.session_state.messages.extend([
                            {"role": "user", "content": transcribed_text},
                            {"role": "assistant", "content": bot_response}
                        ])
                        st.success(f"Transcribed: {transcribed_text}")
                        st.info(f"Response: {bot_response}")
                    os.remove(audio_file_path)
                st.session_state.recording_state = "stopped"
    
    with col2:
        st.write("📁 Audio File Upload")
        audio_file = st.file_uploader("Upload audio (WAV format):", type=["wav"])
        
        if audio_file and st.button("Process Audio"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                temp_file.write(audio_file.getvalue())
                temp_path = temp_file.name
            
            with st.spinner("Processing audio..."):
                transcribed_text, bot_response = process_audio_to_chat(temp_path)
            
            if transcribed_text:
                st.session_state.messages.extend([
                    {"role": "user", "content": transcribed_text},
                    {"role": "assistant", "content": bot_response}
                ])
                st.success(f"Transcribed: {transcribed_text}")
                st.info(f"Response: {bot_response}")
            
            os.remove(temp_path)

    # Display conversation history
    st.write("💭 Conversation History")
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])