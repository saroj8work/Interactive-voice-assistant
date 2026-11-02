"""
Text-to-Speech (TTS) Module.
Converts agent textual responses into audio format (WAV/MP3) for client playback.
"""
import io
import wave
import math
import struct
import base64
import logging
from typing import Optional, Tuple

logger = logging.getLogger("voice_agent.tts")

try:
    import pyttsx3
    HAS_PYTTSX3 = True
except ImportError:
    HAS_PYTTSX3 = False


class TextToSpeechService:
    """
    Synthesizes text into audio waveforms.
    """

    def synthesize(self, text: str) -> Tuple[bytes, str]:
        """
        Synthesizes text and returns (audio_bytes, mime_type).
        """
        if HAS_PYTTSX3:
            try:
                engine = pyttsx3.init()
                engine.setProperty("rate", 160)
                # Save to in-memory bytes if supported or file
                # Pyttsx3 save_to_file
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    temp_path = f.name
                engine.save_to_file(text, temp_path)
                engine.runAndWait()
                with open(temp_path, "rb") as f:
                    data = f.read()
                import os
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
                if len(data) > 44:  # Valid WAV file
                    return data, "audio/wav"
            except Exception as e:
                logger.warning(f"pyttsx3 synthesis failed: {e}")

        # Fallback: Generate an auditory acknowledgement audio tone (synthesized pleasant chime WAV)
        return self._generate_chime_wav(), "audio/wav"

    def synthesize_to_base64(self, text: str) -> str:
        """
        Synthesizes text and returns a base64 encoded string.
        """
        audio_bytes, _ = self.synthesize(text)
        return base64.b64encode(audio_bytes).decode("ascii")

    def _generate_chime_wav(self) -> bytes:
        """
        Generates a valid lightweight audio/wav chime tone (440Hz -> 880Hz).
        Guarantees that every REST API call receives playable valid audio without external dependencies.
        """
        sample_rate = 16000
        duration_seconds = 0.4
        num_samples = int(sample_rate * duration_seconds)

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)

            samples = []
            for i in range(num_samples):
                t = i / sample_rate
                # Frequency glide from 440 to 660
                freq = 440 + (220 * (i / num_samples))
                # Soft envelope
                envelope = math.sin(math.pi * (i / num_samples))
                val = int(16000 * envelope * math.sin(2 * math.pi * freq * t))
                samples.append(struct.pack("<h", val))

            wav_file.writeframes(b"".join(samples))

        return buffer.getvalue()


tts_service = TextToSpeechService()
