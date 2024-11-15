import os
import pyaudio
from google.cloud import speech
import queue

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "sa_speech_demo.json"

RATE = 16000
CHUNK = int(RATE / 10)

keywords_es = ["ayuda", "agua", "comida", "medicina", "rescate", "refugio",
               "familia", "emergencia", "salud", "comunicación"]

class MicrophoneStream:
    def __init__(self, rate, chunk):
        self.rate = rate
        self.chunk = chunk
        self.buff = queue.Queue()
        self.closed = True

    def __enter__(self):
        self.audio_interface = pyaudio.PyAudio()
        self.audio_stream = self.audio_interface.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk,
            stream_callback=self._fill_buffer,
        )
        self.closed = False
        return self

    def __exit__(self, type, value, traceback):
        self.audio_stream.stop_stream()
        self.audio_stream.close()
        self.closed = True
        self.buff.put(None)
        self.audio_interface.terminate()

    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        self.buff.put(in_data)
        return None, pyaudio.paContinue

    def generator(self):
        while not self.closed:
            chunk = self.buff.get()
            if chunk is None:
                return
            data = [chunk]

            while True:
                try:
                    chunk = self.buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break

            yield b"".join(data)

def listen_print_loop(responses, file_path, stream):
    with open(file_path, 'w') as f:
        for response in responses:
            if not response.results:
                continue

            result = response.results[0]
            if not result.alternatives:
                continue

            transcript = result.alternatives[0].transcript.lower()
            print(f'Transcript: {transcript}')
            f.write(f'Transcript: {transcript}\n')

            for keyword in keywords_es:
                if keyword in transcript:
                    print(f'Palabra clave reconocida: {keyword}')
                    f.write(f'Palabra clave reconocida: {keyword}\n')
                    if keyword == "salir":
                        stream.closed = True
                        return

def transcribe_es():
    client = speech.SpeechClient()
    file_path = 'transcript_es.txt'

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code="es-ES",
    )

    streaming_config = speech.StreamingRecognitionConfig(
        config=config,
        interim_results=True,
    )

    with MicrophoneStream(RATE, CHUNK) as stream:
        audio_generator = stream.generator()
        requests = (speech.StreamingRecognizeRequest(audio_content=content)
                    for content in audio_generator)

        responses = client.streaming_recognize(streaming_config, requests)

        listen_print_loop(responses, file_path, stream)

if __name__ == "__main__":
    transcribe_es()
