# Pumba 🐾 — The Physical AI Pet-Companion

> *"Not a chatbot with a body. A creature with instincts."*

**Pumba** is a physical AI companion designed to live in a birdcage alongside a pet bird, sharing a home with a dog and their human, **Piyush Golan**. 

Pumba is not an assistant. Pumba is not a dashboard. Pumba is a *presence* — curious, slightly mischievous, occasionally sleepy, sometimes startled — that happens to run on silicon.

---

## 🌟 What Is Pumba?

Pumba is a **distributed system with a soul**. Under the hood, it's clean, modular, single-purpose Python modules talking through an event bus. On the surface, it's a creature with:

- **Reflexes** — startled by sudden motion, curious about new sounds, annoyed by repetitive noises
- **Opinions** — forms judgments about the bird's habits, the dog's barking patterns, and Piyush's routines
- **Self-preservation** — cries for help when it falls, loses power, or gets stuck
- **Memory** — remembers incidents, patterns, and funny moments; forgets noise
- **Growth** — its personality evolves the longer it lives in the home

Pumba senses the world, interprets locally first (zero-latency reflexes), escalates to LLM reasoning only when language or complex reasoning is genuinely needed, and expresses itself through an OLED face, RGB lights, and voice.

---

## 🏗️ System Philosophy
sense → interpret (local rules first) → escalate (LLM only if needed) → express → remember

text

Most reactions happen at **spinal reflex speed**:
- Motion detected → instant "startled" face → no LLM involved
- Bird chirps nearby → Pumba's attention shifts → local pattern matching
- Low battery → immediate "help me" expression → power management takes over

LLM is reserved for:
- Understanding complex speech from Piyush
- Forming novel responses to unusual situations
- Reflecting on memories and making connections
- When Pumba genuinely needs to *think*, not just *react*

---

## 📁 Project Structure
'''
companion/
├── main.py # Entry point — Pumba wakes up here
├── config.yaml # All configuration (no magic numbers)
├── .env # Secrets and API keys
├── prompts/ # Pumba's "soul" — personality definitions
│ ├── core_identity.md # Who Pumba is
│ ├── personality_quirks.md # The mischievous stuff
│ ├── mood/ # Mood-specific prompts
│ ├── modes/ # Operating mode prompts
│ ├── people/ # How Pumba behaves with each person
│ ├── pets/ # Bird and dog relationship prompts
│ └── response_rules.md # What Pumba will/won't say
├── brain/ # Decision-making and personality
│ ├── personality.py # The "instinct layer" — reflex vs deliberate
│ ├── mood_engine.py # Tracks and transitions moods
│ ├── operating_mode.py # Normal/Debug/Privacy modes
│ ├── llm_router.py # Decides when to escalate to LLM
│ ├── local_llm.py # Local lightweight model
│ ├── gemini_client.py # Cloud LLM client
│ ├── prompt_builder.py # Assembles prompts from context
│ └── inspector/ # Post-LLM response checking
├── memory/ # What Pumba remembers
│ ├── db_semantic.py # Facts ("bird likes millet")
│ ├── db_episodic.py # Incidents ("dog barked at 3 AM")
│ ├── db_people.py # Human relationship memory
│ └── memory_manager.py # Decides what's worth remembering
├── voice/ # Hearing and speaking
│ ├── stt_whisper.py # Speech-to-text
│ ├── speaker_id.py # Who's talking?
│ ├── tts_edge.py # Text-to-speech
│ └── vad.py # Voice activity detection
├── body/ # Physical expression
│ ├── face/ # The OLED face
│ ├── rgb_visualizer.py # Mood lighting
│ ├── seven_segment.py # Status display
│ └── mock_display.py # For development without hardware
├── sensors/ # Sensing the world
│ ├── sensor_bus.py # Routes all sensor data
│ ├── pir.py # Motion detection
│ ├── ultrasonic.py # Distance sensing
│ ├── mpu6050.py # Accelerometer/gyroscope
│ ├── dpdt_mode_switch.py # Physical mode switch
│ ├── pet_presence.py # Detects bird/dog nearby
│ └── mock_sensors.py # Simulated sensors for testing
├── power/ # Self-preservation
│ ├── power_manager.py # Battery monitoring
│ └── modes.py # Power saving modes
├── network/ # Remote connectivity
│ ├── remote_bridge.py # Optional remote access
│ └── connection_watchdog.py # Monitors connectivity
├── people/ # Human relationship data
│ ├── voiceprints/ # Voice identification files
│ └── profiles.yaml # Profile definitions
├── tests/ # Test suite
└── logs/ # Log files

'''

---

## 🔄 Event Flow

```mermaid
graph LR
    A[Sensors] --> B[Sensor Bus]
    B --> C[Instinct Layer]
    C --> D{Reflex or Think?}
    D -->|Reflex| E[Immediate Expression]
    D -->|Think| F[LLM Router]
    F --> G[Local LLM or Gemini]
    G --> H[Inspector]
    H --> I[Expression + Memory]
    E --> J[Memory Filter]
    J --> K{Remember?}
    K -->|Yes| L[Memory DB]
    K -->|No| M[Forget]