import os
import pyaudio
from google.cloud import speech
import queue
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account

# GCP hizmet hesabı anahtar dosyanızın yolunu ayarlayın
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "sa_speech_demo.json"

# Ses dinleme parametreleri
RATE = 16000
CHUNK = int(RATE / 10)  # 100ms

# Anahtar kelimeler listesi
keywords_tr = ["yardım", "destek", "imdat", "acil", "kurtarın", "beni duyan var mı",
               "sesimi duyan var mı", "yardıma ihtiyacım var", "hey", "çıkış"]

keywords_en = ["help", "trapped", "emergency", "rescue", "injured", "stuck", "save",
               "need", "aid", "urgent", "exit"]

keywords_fr = ["aide", "urgent", "sauvez-moi", "danger", "pompier", "ambulance",
               "aidez-moi", "s'il vous plaît", "blessé", "perdu"]

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

            # Anahtar kelimeleri kontrol et
            for keyword in keywords_tr + keywords_en + keywords_fr + keywords_es:
                if keyword in transcript:
                    print(f'Kelime tanındı: {keyword}')
                    f.write(f'Kelime tanındı: {keyword}\n')
                    # Eğer çıkış komutu algılandıysa döngüyü sonlandır
                    if keyword in ["çıkış", "exit", "fin", "salir"]:
                        stream.closed = True
                        return

def upload_to_drive(file_path):
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    SERVICE_ACCOUNT_FILE = 'sa_speech_demo.json'

    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('drive', 'v3', credentials=credentials)

    file_metadata = {'name': os.path.basename(file_path)}
    media = MediaFileUpload(file_path, mimetype='text/plain')

    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    print(f'File ID: {file.get("id")}')

def main():
    client = speech.SpeechClient()
    file_path = 'transcript.txt'

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code="en-US",  # İlk dil İngilizce
        alternative_language_codes=["tr-TR", "fr-FR", "es-ES"],  # Alternatif diller
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

    upload_to_drive(file_path)

if __name__ == "__main__":
    main()
