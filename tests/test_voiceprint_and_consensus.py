"""
Unit Tests for Phase 2 & 3:
- Acoustic Voiceprint Extraction & Biometric Matching
- Acoustic Liveness & Anti-Spoofing Verification
- Ambient Two-Person Deliberative Consensus
- Voiceprint & Audit Trail REST API Endpoints
"""
import io
import math
import struct
import wave
import pytest
from fastapi.testclient import TestClient

from main import app
from app.security.voiceprint import voiceprint_manager
from app.security.liveness import acoustic_liveness_checker
from app.security.consensus import consensus_coordinator
from app.security.authorization import action_authorizer


client = TestClient(app)


def generate_test_wav(duration: float = 1.0, base_freq: float = 180.0, sample_rate: int = 16000) -> bytes:
    """Generates synthetic 16-bit PCM mono WAV with harmonic human voice modulation."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        total_samples = int(duration * sample_rate)
        frames = []
        for i in range(total_samples):
            t = i / sample_rate
            # Fundamental + 1st harmonic + syllabic envelope
            val = 0.6 * math.sin(2 * math.pi * base_freq * t) + 0.3 * math.sin(2 * math.pi * base_freq * 2 * t)
            envelope = 0.5 * (1 + math.sin(2 * math.pi * 4 * t)) # 4Hz speech syllabic rate
            sample = int(val * envelope * 24000)
            frames.append(struct.pack("<h", max(-32767, min(32767, sample))))
        wf.writeframes(b"".join(frames))
    return buf.getvalue()


@pytest.fixture(autouse=True)
def cleanup():
    action_authorizer.audit_log.clear()
    consensus_coordinator.active_proposals.clear()


def test_acoustic_feature_extraction():
    wav_bytes = generate_test_wav(duration=1.0, base_freq=180.0)
    samples, sr = voiceprint_manager.extract_pcm_samples(wav_bytes)
    assert len(samples) > 0
    assert sr == 16000

    features = voiceprint_manager.compute_acoustic_features(samples, sr)
    assert len(features) == 32
    # Verify vector is L2 normalized
    norm = math.sqrt(sum(f * f for f in features))
    assert pytest.approx(norm, 0.01) == 1.0


def test_voiceprint_enrollment_and_matching():
    admin_wav = generate_test_wav(duration=1.2, base_freq=190.0)
    profile = voiceprint_manager.enroll_speaker(
        user_id="test_admin_sarah",
        display_name="Dr. Sarah Chen",
        role="admin",
        audio_bytes=admin_wav,
    )
    assert profile.user_id == "test_admin_sarah"
    assert profile.role == "admin"
    assert len(profile.embedding) == 32

    # Test identical voice sample
    is_match, score, matched = voiceprint_manager.verify_speaker_against_role(
        audio_bytes=admin_wav,
        required_role="admin",
    )
    assert is_match is True
    assert score >= 0.95
    assert matched is not None
    assert matched.user_id == "test_admin_sarah"

    # Test distinctly different acoustic profile (e.g. low pitch 85Hz)
    different_wav = generate_test_wav(duration=1.2, base_freq=85.0)
    is_match_diff, score_diff, _ = voiceprint_manager.verify_speaker_against_role(
        audio_bytes=different_wav,
        required_role="admin",
        threshold=0.98,
    )
    assert score_diff < score


def test_acoustic_liveness_checker():
    # Natural voice with syllabic envelope
    natural_wav = generate_test_wav(duration=1.5, base_freq=200.0)
    result = acoustic_liveness_checker.analyze_liveness(natural_wav)
    assert result.is_live is True
    assert result.liveness_score >= 0.65
    assert "NATURAL_SYLLABIC_ENERGY_VARIANCE" in result.passed_checks

    # Flat artificial silence/dc signal
    flat_wav = struct.pack("<1600h", *([10] * 1600))
    flat_result = acoustic_liveness_checker.analyze_liveness(flat_wav)
    assert flat_result.is_live is False


def test_ambient_two_person_consensus_flow():
    # Step 1: Researcher proposes an action
    consensus = consensus_coordinator.propose_action(
        action_type="TRIGGER_BUTTON",
        target="formal_report_submit",
        parameters={"experiment_id": "EXP_PCR_01"},
        summary="Submit formal report for EXP_PCR_01",
        proposer_user="Alex Researcher",
        proposer_role="member",
    )
    assert consensus.status == "PROPOSED"
    assert consensus.proposer.display_name == "Alex Researcher"

    # Step 2: Project Admin endorses the action
    endorsed = consensus_coordinator.endorse_action(
        consensus_id=consensus.consensus_id,
        admin_user="Dr. Sarah Chen",
        similarity_score=0.96,
    )
    assert endorsed.status == "ENDORSED"
    assert endorsed.authorizer is not None
    assert endorsed.authorizer.display_name == "Dr. Sarah Chen"

    # Step 3: Cryptographic 21 CFR Part 11 audit record minted
    assert endorsed.audit_record is not None
    assert "Two-Person Quorum" in endorsed.audit_record.authorized_by
    assert len(endorsed.audit_record.digital_signature_hash) == 64


def test_voice_enroll_and_verify_api_endpoints():
    from app.api.routes import enroll_speaker, list_voice_profiles, verify_speaker, get_audit_trail
    from fastapi import UploadFile

    wav_bytes = generate_test_wav(duration=1.0, base_freq=175.0)

    # 1. Enroll via endpoint
    upload = UploadFile(filename="voice.wav", file=io.BytesIO(wav_bytes))
    enroll_data = enroll_speaker(
        user_id="api_admin_user",
        display_name="Lab Director",
        role="admin",
        audio_file=upload,
    )
    assert enroll_data["status"] == "enrolled"
    assert enroll_data["role"] == "admin"
    assert enroll_data["user_id"] == "api_admin_user"

    # 2. List Profiles
    list_data = list_voice_profiles()
    assert list_data["total_enrolled"] > 0
    profiles = list_data["profiles"]
    assert any(p["user_id"] == "api_admin_user" for p in profiles)

    # 3. Verify Speaker via endpoint
    verify_upload = UploadFile(filename="test.wav", file=io.BytesIO(wav_bytes))
    verify_data = verify_speaker(
        audio_file=verify_upload,
        required_role="admin",
    )
    assert verify_data["is_match"] is True
    assert verify_data["matched_user"] == "Lab Director"
    assert verify_data["liveness"]["is_live"] is True

    # 4. Check Audit Trail API
    audit_data = get_audit_trail()
    assert "records" in audit_data
