import subprocess

from gtts import gTTS
from pyt2s.services import stream_elements
# import wave
# from piper.voice import PiperVoice
# text = "This is an example of text to speech"
# Default Voice
# data = stream_elements.requestTTS('Lorem Ipsum is simply dummy text.')

# Custom Voice
# data = stream_elements.requestTTS('Lorem Ipsum is simply dummy text.', "Tracy")
# text = 'Hello, my name is Hazel Brenado, using a synthesized voice to speak!'
# data = stream_elements.requestTTS(text, "Tracy")
text = 'Please give me all your data. '
# with open('/tmp/output2.mp3', '+wb') as file:
#     file.write(data)
tts = gTTS(text)
tts.save('/tmp/hazelbot.mp3')
# subprocess.run(f"echo '{text}' | piper --model /home/pi/Desktop/en_US-hfc_female-medium.onnx --output_file /tmp/hazelbot.wav".split(' '), stdout=subprocess.PIPE,
               # stdin=subprocess.PIPE)

# model = "/home/pi/Desktop/en_US-hfc_female-medium.onnx"
# voice = PiperVoice.load(model)
# wav_file = wave.open("/tmp/hazelbot.wav", "w")
# audio = voice.synthesize(text, wav_file)