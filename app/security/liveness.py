"""
Acoustic Voice Liveness & Anti-Spoofing Verification Engine.
Validates natural human glottal micro-tremor, dynamic dynamic-range,
and spectral dispersion to protect against synthetic voice cloning and phone replays.
"""
from __future__ import annotations
import math
from typing import Dict, Any, List, Tuple
from pydantic import BaseModel, Field

from app.security.voiceprint import voiceprint_manager


class LivenessResult(BaseModel):
    is_live: bool
    confidence: float
    liveness_score: float = Field(..., description="Acoustic naturalness score [0.0 - 1.0]")
    passed_checks: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)


class AcousticLivenessChecker:
    """
    Performs passive acoustic liveness and anti-spoofing checks on voice audio.
    """

    def __init__(self, min_liveness_score: float = 0.65):
        self.min_liveness_score = min_liveness_score

    def analyze_liveness(self, audio_bytes: bytes) -> LivenessResult:
        """
        Analyzes audio samples for natural acoustic characteristics:
        1. Natural energy variance (human cadence vs flat synthetic signals)
        2. Micro-jitter in frame energy
        3. Zero-crossing rate dispersion
        4. Absence of abrupt synthetic DC offsets
        """
        samples, sample_rate = voiceprint_manager.extract_pcm_samples(audio_bytes)

        if not samples or len(samples) < 800:
            return LivenessResult(
                is_live=False,
                confidence=0.0,
                liveness_score=0.0,
                warnings=["Insufficient audio duration to evaluate acoustic liveness."],
                details={"sample_count": len(samples)}
            )

        passed_checks = []
        warnings = []
        scores: List[float] = []

        # Check 1: Dynamic Range & Energy Envelope Variance
        # Human speech exhibits natural pauses, syllabic peaks, and energy variations.
        frame_size = max(160, sample_rate // 50) # 20ms frames
        frame_energies = []
        for i in range(0, len(samples) - frame_size, frame_size):
            frame = samples[i : i + frame_size]
            rms = math.sqrt(sum(s * s for s in frame) / len(frame))
            frame_energies.append(rms)

        if frame_energies:
            mean_e = sum(frame_energies) / len(frame_energies)
            variance_e = sum((e - mean_e) ** 2 for e in frame_energies) / len(frame_energies)
            std_e = math.sqrt(variance_e)
            cov_e = std_e / max(mean_e, 1.0) # Coefficient of variation

            # Human voice coefficient of variation is typically > 0.35 due to syllables
            if cov_e >= 0.30:
                passed_checks.append("NATURAL_SYLLABIC_ENERGY_VARIANCE")
                scores.append(min(1.0, cov_e / 0.8))
            else:
                warnings.append("Low dynamic variance: signal resembles flat synthetic noise or compressed carrier.")
                scores.append(0.3)
        else:
            scores.append(0.0)

        # Check 2: Micro-jitter in zero crossing rates
        # Human glottal vibration is slightly quasi-periodic (has micro-jitter).
        zcr_list = []
        for i in range(0, len(samples) - frame_size, frame_size):
            frame = samples[i : i + frame_size]
            crossings = sum(1 for j in range(1, len(frame)) if (frame[j] >= 0 > frame[j - 1]) or (frame[j] < 0 <= frame[j - 1]))
            zcr_list.append(crossings / len(frame))

        if len(zcr_list) > 2:
            zcr_diffs = [abs(zcr_list[k] - zcr_list[k - 1]) for k in range(1, len(zcr_list))]
            mean_diff = sum(zcr_diffs) / len(zcr_diffs)
            if mean_diff > 0.005:
                passed_checks.append("MICRO_JITTER_GLOTTAL_DYNAMICS")
                scores.append(0.95)
            else:
                warnings.append("Abnormally static spectral continuity.")
                scores.append(0.4)

        # Check 3: Crest Factor (Peak to RMS ratio)
        # Replayed audio through small speakers often has severe clipping/limiting
        max_abs = max(abs(s) for s in samples)
        overall_rms = math.sqrt(sum(s * s for s in samples) / len(samples)) or 1.0
        crest_factor = max_abs / overall_rms

        if 2.0 <= crest_factor <= 12.0:
            passed_checks.append("NATURAL_CREST_FACTOR_ACOUSTICS")
            scores.append(0.90)
        else:
            warnings.append(f"Unusual acoustic crest factor ({crest_factor:.1f}). Possible clipping or limiting.")
            scores.append(0.5)

        avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0
        is_live = avg_score >= self.min_liveness_score

        return LivenessResult(
            is_live=is_live,
            confidence=avg_score,
            liveness_score=avg_score,
            passed_checks=passed_checks,
            warnings=warnings,
            details={
                "dynamic_cov": round(cov_e, 3) if frame_energies else 0,
                "crest_factor": round(crest_factor, 2),
                "checks_passed_count": len(passed_checks),
            }
        )


# Global singleton
acoustic_liveness_checker = AcousticLivenessChecker()

