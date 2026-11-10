"""
Acoustic Speaker Biometrics & Voiceprint Enrollment Engine.
Pure Python implementation (zero external C-extension dependencies).
Extracts normalized acoustic feature vectors (energy envelope, pitch autocorrelation,
zero-crossing rates, and spectral band ratios) to identify and authenticate speakers.
"""
from __future__ import annotations
import io
import json
import math
import struct
import time
import wave
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.config import settings

VOICEPRINTS_DIR = settings.data_dir / "voiceprints"
VOICEPRINTS_DIR.mkdir(parents=True, exist_ok=True)


class VoiceprintProfile(BaseModel):
    user_id: str
    display_name: str
    role: str # "admin", "member"
    embedding: List[float] = Field(..., description="Normalized 32-dimensional acoustic feature vector")
    enrolled_at: float = Field(default_factory=time.time)
    sample_duration_sec: float = 0.0
    is_active: bool = True


class VoiceprintManager:
    """
    Manages speaker voice enrollment, acoustic feature extraction,
    and biometric verification via cosine similarity.
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or VOICEPRINTS_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.similarity_threshold = 0.82

    def extract_pcm_samples(self, audio_bytes: bytes) -> Tuple[List[int], int]:
        """
        Parses WAV audio bytes into 16-bit PCM integer samples and returns (samples, sample_rate).
        If audio is not valid WAV, gracefully handles raw PCM or synthetic buffers.
        """
        try:
            with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
                sample_rate = wf.getframerate()
                num_channels = wf.getnchannels()
                sample_width = wf.getsampwidth()
                num_frames = wf.getnframes()
                raw_data = wf.readframes(num_frames)

                if sample_width == 2:
                    fmt = f"<{num_frames * num_channels}h"
                    all_samples = struct.unpack(fmt, raw_data)
                    # Downmix to mono if stereo
                    if num_channels > 1:
                        mono = [all_samples[i] for i in range(0, len(all_samples), num_channels)]
                        return mono, sample_rate
                    return list(all_samples), sample_rate
                elif sample_width == 1:
                    # 8-bit unsigned PCM
                    mono = [s - 128 for s in raw_data]
                    return mono, sample_rate
        except Exception:
            pass

        # Fallback: Treat as raw 16-bit PCM mono 16kHz
        count = len(audio_bytes) // 2
        if count > 0:
            samples = struct.unpack(f"<{count}h", audio_bytes[:count * 2])
            return list(samples), 16000
        return [0] * 1600, 16000

    def compute_acoustic_features(self, samples: List[int], sample_rate: int = 16000) -> List[float]:
        """
        Extracts a fixed 32-dimensional acoustic embedding vector:
        - Temporal RMS energy distribution (8 features)
        - Zero Crossing Rate distribution (8 features)
        - Autocorrelation / Pitch estimates (8 features)
        - Spectral band ratio estimates (8 features)
        """
        if not samples:
            return [0.0] * 32

        # 1. Temporal RMS Energy (8 temporal segments)
        seg_len = max(1, len(samples) // 8)
        energy_feats: List[float] = []
        for i in range(8):
            seg = samples[i * seg_len : (i + 1) * seg_len]
            if seg:
                rms = math.sqrt(sum(s * s for s in seg) / len(seg))
                energy_feats.append(rms)
            else:
                energy_feats.append(0.0)

        # Normalize energy features
        max_e = max(energy_feats) if energy_feats and max(energy_feats) > 0 else 1.0
        energy_feats = [e / max_e for e in energy_feats]

        # 2. Zero Crossing Rate (8 temporal segments)
        zcr_feats: List[float] = []
        for i in range(8):
            seg = samples[i * seg_len : (i + 1) * seg_len]
            if len(seg) > 1:
                crossings = sum(1 for j in range(1, len(seg)) if (seg[j] >= 0 > seg[j - 1]) or (seg[j] < 0 <= seg[j - 1]))
                zcr = crossings / len(seg)
                zcr_feats.append(zcr)
            else:
                zcr_feats.append(0.0)

        # 3. Autocorrelation / Fundamental Pitch characteristics (8 lag windows: 20 to 120 samples)
        # Covers human pitch range ~80Hz to ~400Hz at 16kHz
        autocorr_feats: List[float] = []
        window = samples[: min(len(samples), 2000)]
        for lag in [25, 40, 55, 70, 85, 100, 115, 130]:
            if len(window) > lag:
                corr = sum(window[k] * window[k + lag] for k in range(len(window) - lag))
                norm = math.sqrt(sum(s * s for s in window) * sum(s * s for s in window[lag:])) or 1.0
                autocorr_feats.append(max(0.0, corr / norm))
            else:
                autocorr_feats.append(0.0)

        # 4. Spectral Difference / Filter Frequency Ratios (8 differences)
        spec_feats: List[float] = []
        # Pre-emphasis filter to approximate high-frequency formant distribution
        filtered = [samples[k] - 0.95 * samples[k - 1] for k in range(1, min(len(samples), 3000))]
        f_seg_len = max(1, len(filtered) // 8)
        for i in range(8):
            f_seg = filtered[i * f_seg_len : (i + 1) * f_seg_len]
            if f_seg:
                f_rms = math.sqrt(sum(s * s for s in f_seg) / len(f_seg))
                spec_feats.append(f_rms)
            else:
                spec_feats.append(0.0)
        max_s = max(spec_feats) if spec_feats and max(spec_feats) > 0 else 1.0
        spec_feats = [s / max_s for s in spec_feats]

        # Combine all 32 dimensions
        raw_vector = energy_feats + zcr_feats + autocorr_feats + spec_feats

        # L2-normalize vector to unit length for cosine similarity
        norm_l2 = math.sqrt(sum(v * v for v in raw_vector)) or 1.0
        return [round(v / norm_l2, 6) for v in raw_vector]

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Computes the cosine similarity between two feature vectors [-1.0, 1.0]."""
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        norm_a = math.sqrt(sum(a * a for a in v1)) or 1.0
        norm_b = math.sqrt(sum(b * b for b in v2)) or 1.0
        return round(dot / (norm_a * norm_b), 4)

    def enroll_speaker(
        self,
        user_id: str,
        display_name: str,
        role: str,
        audio_bytes: bytes,
    ) -> VoiceprintProfile:
        """Enrolls a user's voiceprint from audio samples and persists to disk."""
        samples, sample_rate = self.extract_pcm_samples(audio_bytes)
        duration_sec = round(len(samples) / max(sample_rate, 1), 2)
        embedding = self.compute_acoustic_features(samples, sample_rate)

        profile = VoiceprintProfile(
            user_id=user_id,
            display_name=display_name,
            role=role.lower().strip(),
            embedding=embedding,
            enrolled_at=time.time(),
            sample_duration_sec=duration_sec,
            is_active=True,
        )

        file_path = self.storage_dir / f"{user_id}.json"
        file_path.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
        return profile

    def get_profile(self, user_id: str) -> Optional[VoiceprintProfile]:
        """Loads an enrolled voiceprint from disk."""
        file_path = self.storage_dir / f"{user_id}.json"
        if not file_path.exists():
            return None
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            return VoiceprintProfile(**data)
        except Exception:
            return None

    def list_profiles(self) -> List[VoiceprintProfile]:
        """Lists all enrolled voice profiles."""
        profiles = []
        for file in self.storage_dir.glob("*.json"):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                profiles.append(VoiceprintProfile(**data))
            except Exception:
                continue
        return profiles

    def verify_speaker_against_role(
        self,
        audio_bytes: bytes,
        required_role: str = "admin",
        threshold: Optional[float] = None,
    ) -> Tuple[bool, float, Optional[VoiceprintProfile]]:
        """
        Verifies if incoming speech audio matches an enrolled speaker having the required role.
        Returns: (is_match, similarity_score, matched_profile)
        """
        thresh = threshold or self.similarity_threshold
        samples, sample_rate = self.extract_pcm_samples(audio_bytes)
        incoming_embedding = self.compute_acoustic_features(samples, sample_rate)

        best_score = 0.0
        best_profile: Optional[VoiceprintProfile] = None

        for profile in self.list_profiles():
            if profile.role == required_role.lower().strip() and profile.is_active:
                score = self.cosine_similarity(incoming_embedding, profile.embedding)
                if score > best_score:
                    best_score = score
                    best_profile = profile

        is_match = best_score >= thresh
        return is_match, best_score, best_profile


# Global singleton
voiceprint_manager = VoiceprintManager()

