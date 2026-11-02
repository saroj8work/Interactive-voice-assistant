# Voice Assistant Domain Knowledge Base

## Overview
Welcome to the Voice Assistant Knowledge Base. This document provides core operational knowledge, device policies, action playbooks, and service guides used by the conversational voice agent.

## Operating Hours and Support
- **Support Hours**: Monday to Friday, 9:00 AM to 6:00 PM EST.
- **Emergency Contact**: For critical system failures, contact the site reliability engineering team at `sre-urgent@example.com` or dial extension 9911.
- **Self-Service**: Users can check system status, query logs, and run automated diagnostics 24/7.

## Voice Assistant Capabilities & Actions
The voice assistant is equipped with the following conversational capabilities:
1. **Weather Inquiries**: Retrieves real-time temperature, humidity, and forecasts worldwide using Open-Meteo services.
2. **Mathematical Calculations**: Solves arithmetic, percentages, tips, unit conversions, and algebraic formulas safely.
3. **Task & Note Management**: Creates, retrieves, and organizes notes, memos, and logs stored locally on disk.
4. **Productivity Timers**: Sets background countdown timers and reminders with custom labels.
5. **System Diagnostics**: Monitors CPU core count, operating system details, memory status, and current date/time.
6. **Domain Knowledge QA**: Answers questions based directly on this Markdown documentation.

## Refund and Cancellation Policy
- **Standard Refund Window**: Customers can request a full refund within 30 days of initial purchase.
- **Hardware Returns**: Items must be in original condition with all cables and accessories included.
- **Processing Time**: Approved refunds are credited to the original payment method within 3 to 5 business days.
- **Action Playbook**: If a user asks about refunds, provide the 30-day window and offer to record a support note with their request.

## Smart Device Control & Automation Rules
- **Living Room Lights**: Can be dimmed from 0% to 100%. Preset modes include "Movie Night" (20% warm), "Reading" (70% neutral), and "Full Bright" (100%).
- **Thermostat Presets**:
  - Eco Mode: 19°C (Winter) / 24°C (Summer).
  - Comfort Mode: 21°C (Winter) / 22°C (Summer).
- **Safety Rule**: If room temperature exceeds 35°C or drops below 5°C, an automatic alert note must be generated.

## Technical Architecture & Security
- **Backend Stack**: Python 3.12, FastAPI, Pydantic, and Uvicorn.
- **Speech Ingestion**: Supports raw audio files (WAV, MP3, WEBM), base64 streams, and client-side transcription.
- **Safety Standard**: Mathematical evaluations use strict Abstract Syntax Tree (AST) parsing; arbitrary shell execution is disabled.
- **Data Privacy**: Local notes and logs are persisted strictly on the host filesystem under `./data/notes` with zero unauthorized external transmission.
