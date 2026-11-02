# Conversational Voice Assistant Agent: Workflow & Execution Flow

This document details the complete end-to-end operational workflow of the Interactive Conversational Voice Assistant Agent, including flow diagrams, architectural stages, decision logic, and concrete dialogue execution traces.

---

## 1. End-to-End Pipeline Flow Diagram

```mermaid
flowchart TD
    classDef client fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    classDef nlu fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px;
    classDef kb fill:#fff3e0,stroke:#f57c00,stroke-width:2px;
    classDef plan fill:#e8f5e9,stroke:#388e3c,stroke-width:2px;
    classDef tools fill:#fffde7,stroke:#fbc02d,stroke-width:2px;
    classDef output fill:#fbe9e7,stroke:#d84315,stroke-width:2px;

    UI["External UI / Client (React, Vue, Flutter, Mobile, Web)"]:::client

    subgraph INGESTION["1. Ingestion & Transcription"]
        ENDPOINT["REST Endpoint: /api/conversation/chat or /api/voice/process-file"]
        STT["Speech-to-Text (STT Service)"]
    end

    subgraph DIALOGUE["2. Conversational Dialogue Management"]
        SESSION["Session History & Memory (app/agent/conversational.py)"]
        COREFER["Context & Coreference Resolver (Resolves 'that', 'there')"]
    end

    subgraph CLASSIFICATION["3. Classification & Domain Knowledge"]
        MD_KB["Domain Knowledge Base (.md Parser) (data/domain_knowledge.md)"]:::kb
        CLASSIFIER["Intent Classifier & PydanticAI Schema (app/nlu/classifier.py)"]:::nlu
        GATE{"Action Required or Casual Chat?"}
    end

    subgraph CHITCHAT["Branch A: Casual Conversation"]
        CHIT_REPLY["Generate Natural Spoken Reply (Greetings, FAQ, Help)"]
    end

    subgraph ACTION_PIPELINE["Branch B: Action Planning & Execution"]
        PLANNER["Action Planner (app/planner/planner.py)"]:::plan
        PLAN_SCHEMA["Structured Multi-Step Plan (PlanSteps with Dependencies)"]:::plan
        
        subgraph TOOL_REGISTRY["Tool Registry (app/tools/)"]:::tools
            T_WEATHER["Open-Meteo Weather Tool"]
            T_CALC["AST Safe Math Calculator"]
            T_NOTES["Local Notes & Disk Storage"]
            T_TIMER["Background Timers & Reminders"]
            T_SYSTEM["System Stats & Utilities"]
            T_KB["Markdown Knowledge Search"]
        end
        
        WRAPPER["Conversational Action Response Formulator"]
    end

    subgraph RESPONSE_SYNTHESIS["4. Speech & Payload Generation"]
        TTS["Text-to-Speech (TTS Service)"]:::output
        FINAL_JSON["Final JSON Payload (Reply + Steps + Audio Base64)"]:::output
    end

    UI -->|"Voice Audio or Text"| ENDPOINT
    ENDPOINT --> STT
    STT -->|"Transcribed Text"| SESSION
    SESSION --> COREFER
    COREFER --> CLASSIFIER
    COREFER -.->|"Query Topics"| MD_KB
    MD_KB -.->|"Inject Relevant Section"| CLASSIFIER

    CLASSIFIER --> GATE

    GATE -->|"Pure Chit-Chat / Greeting"| CHIT_REPLY
    GATE -->|"Action Needed (Weather, Math, Notes, Rules, Timers)"| PLANNER

    PLANNER --> PLAN_SCHEMA
    PLAN_SCHEMA --> TOOL_REGISTRY
    TOOL_REGISTRY --> WRAPPER

    CHIT_REPLY --> TTS
    WRAPPER --> TTS
    TTS --> FINAL_JSON
    FINAL_JSON -->|"Audio Stream + Execution Traces"| UI
```

---

## 2. Detailed Lifecycle Stages

### Stage 1: Ingestion & Speech-to-Text (STT)
1. **Entrypoint**: The external UI calls either:
   * `POST /api/conversation/chat` (JSON with natural conversation text/message)
   * `POST /api/voice/process-file` (Multipart form upload with raw `.wav`, `.mp3`, or `.webm` audio)
   * `POST /api/voice/process-base64` (Base64 audio payload from a browser microphone)
2. **Audio Decoding**: The [`SpeechToTextService`](app/audio/stt.py) transcribes audio into normalized text strings.

### Stage 2: Conversational Dialogue Management & Context Resolution
1. **Dialogue History**: The [`ConversationSession`](app/agent/conversational.py) stores multi-turn context (speaker roles, timestamps, prior actions, and last recorded entities).
2. **Coreference Resolution**:
   * Pronouns like *"that"*, *"it"*, or *"there"* are resolved using dialogue history.
   * *Example*: If the assistant previously shared weather for Tokyo and the user says *"Please note that down"*, the resolver binds *"that"* to the Tokyo weather report.

### Stage 3: Domain Knowledge Retrieval & Intent Classification
1. **Markdown Domain Matching**: Before falling back to generic chit-chat, [`MarkdownDomainKnowledge`](app/knowledge/markdown_loader.py) evaluates [`data/domain_knowledge.md`](data/domain_knowledge.md) for matching business rules, FAQs, support hours, or operating policies.
2. **Intent Classification**: The [`IntentClassifier`](app/nlu/classifier.py) extracts entities and maps the query to one of seven core intents:
   * `weather_query`
   * `calculation_math`
   * `file_note_management`
   * `productivity_timer`
   * `system_control`
   * `web_search_knowledge` (Domain knowledge from `.md`)
   * `conversational_chat` (Casual dialogue / greetings)

### Stage 4: Decision Gate (Action vs. Chit-Chat)
* **Casual Conversation Branch**: If the intent is conversational (e.g., *"Hello"*, *"Who are you?"*, *"Thank you"*), the agent formulates a warm, human reply without executing tools.
* **Action Required Branch**: If the query implies or explicitly requests a task, execution transitions to the **Action Planner**.

### Stage 5: Multi-Step Action Planning
The [`ActionPlanner`](app/planner/planner.py) decomposes the request into an [`ActionPlan`](app/planner/schema.py):
* **Single-Step Plans**: Direct 1-to-1 tool mapping (e.g., weather lookup).
* **Composite Multi-Step Plans**: Resolves dependencies between steps.
  * *Example*: *"Calculate 15% tip on $85 and note it down as Lunch Expense"*
    * `step_1`: Calculator evaluates `(15 / 100) * 85` → outputs `12.75`.
    * `step_2`: Note manager depends on `step_1` and creates a note with the computed result.

### Stage 6: Tool Execution Registry
Each plan step is safely dispatched to registered tools in [`app/tools/`](app/tools/):
* **`weather`**: Queries the Open-Meteo API for real-time conditions.
* **`calculator`**: Safe AST parsing prevents arbitrary code injection.
* **`note_manager`**: Persists notes to disk in `./data/notes/` with indexing.
* **`timer_manager`**: Launches non-blocking background countdown threads.
* **`system`**: Reports host system health and controls whitelisted utility applications.
* **`knowledge_search`**: Retrieves exact sections from the `.md` domain documentation.

### Stage 7: Conversational Response Synthesis & TTS
1. **Response Framing**: Tool output messages are converted into natural conversational spoken phrasing.
2. **Text-to-Speech**: The [`TextToSpeechService`](app/audio/tts.py) synthesizes the speech into playable audio (WAV/Base64).
3. **Payload Delivery**: Returns the complete execution object:
   * `assistant_reply`: Human-like spoken text.
   * `action_identified`: Boolean indicating if an action was executed.
   * `plan`: Full step-by-step plan details.
   * `executed_tools`: Execution traces, output data, and elapsed time.
   * `audio_base64`: Ready-to-play audio stream for the frontend speaker.

---

## 3. Concrete Dialogue Scenarios

### Scenario A: Casual Chit-Chat
* **User**: *"Hi there, what can you help me with?"*
* **Pipeline**:
  * Intent: `conversational_chat`
  * Action Identified: `false`
  * Tools Executed: `None`
* **Assistant Reply**: *"I am your Interactive Voice Assistant Agent! You can chat with me naturally. Whenever you mention tasks like checking the weather, doing math, setting timers, or taking notes, I will automatically identify and perform the action for you."*

### Scenario B: Single Action Request
* **User**: *"What's the weather like in Tokyo right now?"*
* **Pipeline**:
  * Intent: `weather_query` (Entities: `location="Tokyo"`)
  * Action Identified: `true`
  * Tool Executed: `weather`
* **Assistant Reply**: *"The current weather in Tokyo (Japan) is Clear sky with a temperature of 21.2°C, humidity of 48%, and wind speed of 7.4 km/h. Would you like me to note this down or check another city?"*

### Scenario C: Multi-Turn Dialogue with Contextual Coreference
* **Turn 1**: *"What is the weather in London?"*
  * *Assistant reports London weather at 14°C.*
* **Turn 2**: *"Please save that as a travel note"*
  * Context Resolver binds *"that"* to London weather.
  * Tool Executed: `note_manager` (Action: `create`, Content: *"London weather at 14°C"*).
  * *Assistant Reply*: *"Consider it done! I've saved your note: 'Travel note'."*

### Scenario D: Domain Knowledge Ingested from Markdown (`.md`)
* **User**: *"What is your refund policy?"*
* **Pipeline**:
  * Matched Section in `data/domain_knowledge.md`: `## Refund and Cancellation Policy`
  * Action Identified: `true`
  * Tool Executed: `knowledge_search`
* **Assistant Reply**: *"According to the Refund and Cancellation Policy documentation: Standard Refund Window: Customers can request a full refund within 30 days of initial purchase."*

### Scenario E: Composite Multi-Step Action with Parameter Dependency
* **User**: *"Calculate 20% tip on $150 and save note titled Dinner Expense"*
* **Pipeline**:
  * Action Plan:
    * `step_1`: Calculator evaluates `(20 / 100) * 150` → Result: `30`
    * `step_2`: Note manager creates note with title `"Dinner Expense"` and content `"Dinner Expense: 30"`.
  * Action Identified: `true`
* **Assistant Reply**: *"Calculation result for '(20 / 100) * 150' is 30. I've saved your note: 'Dinner Expense'."*

