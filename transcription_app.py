import pyaudio
import websockets
import asyncio
import json
import base64
import os
from dotenv import load_dotenv

import streamlit as st

load_dotenv()


# Mircophone Configuration
FRAMES_PER_BUFFER = 3200
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
p = pyaudio.PyAudio()

# Microphone Stream 
stream = p.open(
    format=FORMAT,
    channels=CHANNELS,
    rate=RATE,
    input=True,
    frames_per_buffer=FRAMES_PER_BUFFER
)


if 'run' not in st.session_state:
    st.session_state['run'] = False
if 'transcription_text' not in st.session_state:
    st.session_state['transcription_text'] = ''


def start_listening():
    st.session_state["run"] = True

def stop_listening():
    st.session_state["run"] = False

def clear_text():
    st.session_state['transcription_text'] = ''

def send_transcription_api():
    # Add your API call logic here
    st.success("Transcription sent!")

st.title("Real Time Transcription")

start, stop = st.columns(2)
start.button("Start Listening", on_click=start_listening)
stop.button("Stop Listening", on_click=stop_listening)

st.text_area("Transcription", value=st.session_state["transcription_text"], height=300, disabled=True)

send_button, clear_button = st.columns(2)
send_button.button("Send Transcription", on_click=send_transcription_api)
clear_button.button("Clear Transcription", on_click=clear_text)

# used for realtime transcription model
ASSEMBLY_URL = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000"

# This constantly sends audio to AssemblyAI and recieves transcription

async def send_recieve():

    print(f'Connecting to {ASSEMBLY_URL}')

    async with websockets.connect(
        ASSEMBLY_URL,
        extra_headers=(("Authorization", os.environ.get("ASSEMBLY_API_KEY")),),
        ping_interval=5,
        ping_timeout=20
    ) as websocket:
        await asyncio.sleep(0.1)
        print("Recieving SessionBegins")
        session_begins = await websocket.recv()

        print(st.session_state['run'])
        # Send audio data to a websocket server at AssemblyAI
        async def send():
            while st.session_state["run"]:
                try:
                    data = stream.read(FRAMES_PER_BUFFER)
                    data = base64.b64encode(data).decode("utf-8")
                    json_data = json.dumps({'audio_data': str(data)})
                    r = await websocket.send(json_data)
                except websockets.exceptions.ConnectionClosedError as e:
                    print("Connection Closed")
                    print(e)
                    assert e.code == 4008
                    break
                except Exception as e:
                    assert False, "Not a websocket 4008 error"
                await asyncio.sleep(0.1)
            return True

        """
            Recieve real time transcription of audio data from AssemblyAI websocket
        """
        async def recieve():
            while st.session_state["run"]:
                try:
                    result_str = await websocket.recv()
                    if json.loads(result_str)['message_type'] == 'FinalTranscript':
                        transcribed_text = json.loads(result_str)['text']
                        st.session_state['transcription_text'] += f"\n{transcribed_text}"
                except websockets.exceptions.ConnectionClosedError as e:
                    print("Connection Closed")
                    print(e)
                    assert e.code == 4008
                    break
                except Exception as e:
                    assert False, "Not a websocket 4008 error"
                await asyncio.sleep(0.1)

        send_result, recieve_result = await asyncio.gather(send(), recieve())


asyncio.run(send_recieve())