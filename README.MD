# 🐾 Pumba — Distributed Physical AI Companion System

> **System ID:** COMPANION-001
> **Deployment:** Birdcage Environment, Multi-Pet Household
> **Primary Operator:** Piyush Golan
> **Architecture:** Event-Driven, Edge-First, Hybrid Local/Cloud Inference

---

## 📋 Technical Specification

### System Overview

Pumba is a real-time embedded AI companion designed for continuous operation in a birdcage environment. The system implements a tiered cognitive architecture with strict latency budgets, prioritizing local reflex responses over cloud-dependent reasoning.

```yaml
Type: Physical AI Companion
Form Factor: Embedded System (Birdcage Deployment)
Compute: Edge Device + Cloud Escalation
Latency Budget:
  Reflex: <50ms
  Local Inference: <200ms
  Cloud Escalation: 500-2000ms
Uptime Target: 99.9% (24/7 operation)
Power: Battery + Potential Solar Assist
```

---

## 🏗️ Architecture

### Core Design Pattern: Event-Driven Microservices

Pumba implements a publish-subscribe event bus pattern where each subsystem operates as an independent service, communicating through typed events. This prevents tight coupling and enables hot-swapping of implementations (e.g., real sensors ↔ mock sensors).

```
┌─────────────────────────────────────────────────────────┐
│                    EVENT BUS (Redis/ZeroMQ)              │
├──────────┬──────────┬──────────┬──────────┬─────────────┤
│ Sensors  │  Brain   │  Memory  │  Voice   │   Body      │
│  Layer   │  Layer   │  Layer   │  Layer   │   Layer     │
├──────────┼──────────┼──────────┼──────────┼─────────────┤
│ PIR      │ Instinct │ Semantic │ VAD      │ OLED        │
│ Ultrason │ Mood     │ Episodic │ SpeakerID│ RGB         │
│ MPU6050  │ LLM Router│ People  │ STT      │ 7-Seg       │
│ DPDT     │ Inspector│ Manager  │ TTS      │ Mock        │
└──────────┴──────────┴──────────┴──────────┴─────────────┘
         ↕           ↕           ↕          ↕
    [Power Manager] [Network] [Config] [Logging]
```

---

## 🧠 Cognitive Architecture

### Tier 1 — Reflex Layer (Zero-Latency)

**Response Time:** <50ms
**Compute:** Local only
**Implementation:** Rule-based state machines

```python
# Example reflex pathway
sensor_bus.publish("motion.detected", {"sensor": "pir", "intensity": 0.8})
    -> instinct_layer.process()               # <10ms
    -> face_controller.trigger("startled")    # <20ms
    -> led_controller.flash("red", duration=100)  # <20ms
```

**Reflexes include:**
- Sudden motion → startle response
- Free-fall detection → panic + brace
- Low battery → sleep mode
- Loud noise → alert + source tracking
- Touch → curiosity/annoyance based on context

### Tier 2 — Local Inference Layer (Edge AI)

**Response Time:** <200ms
**Compute:** On-device (TFLite/ONNX)
**Implementation:** Lightweight ML models

```python
# Local pattern recognition
sensor_bus.subscribe("audio.chunk")
    -> local_classifier.predict(audio_chunk)  # Bird chirp vs dog bark
    -> context_manager.update("pet_presence", {"type": "bird", "confidence": 0.94})
    -> behavior_engine.trigger("bird_attention")
```

**Local models:**
- Pet sound classification (bird chirps vs dog barks)
- Motion pattern recognition
- Voice activity detection
- Emotion classification from audio features
- Anomaly detection for unusual events

### Tier 3 — Deliberative Layer (Cloud LLM)

**Response Time:** 500–2000ms
**Compute:** Cloud (Gemini API)
**Implementation:** Prompt-engineered LLM calls

**Escalation criteria (all must be true):**
1. Local layers cannot resolve the situation
2. Natural language understanding is required
3. Context is novel or ambiguous
4. Response quality benefits from reasoning

```python
# LLM escalation decision matrix
if confidence < THRESHOLD_LOCAL:
    if requires_language_understanding:
        if context_is_novel:
            escalate_to_llm()
        else:
            use_cached_response()
    else:
        use_heuristic_response()
```

---

## 📡 Event Schema

### Sensor Events

```python
# Motion Event
{
    "event_type": "motion.detected",
    "sensor_id": "pir_main",
    "timestamp": 1634567890.123,
    "intensity": 0.87,
    "duration_ms": 450,
    "source_location": "cage_north"
}

# Audio Event
{
    "event_type": "audio.classified",
    "timestamp": 1634567891.456,
    "classification": "bird_vocalization",
    "confidence": 0.93,
    "amplitude_db": 65,
    "frequency_range": [2000, 5000],
    "duration_ms": 230
}

# Motion Sensor (MPU6050)
{
    "event_type": "motion.accelerometer",
    "timestamp": 1634567892.789,
    "accel": {"x": 0.1, "y": 9.8, "z": 0.3},
    "gyro": {"x": 0.01, "y": 0.02, "z": 0.0},
    "orientation": "stable",
    "free_fall_detected": false
}
```

### Behavioral Events

```python
# Mood Transition
{
    "event_type": "mood.changed",
    "from_mood": "curious",
    "to_mood": "excited",
    "trigger": "human_voice_detected",
    "timestamp": 1634567893.012
}

# Memory Formation
{
    "event_type": "memory.formed",
    "memory_type": "episodic",
    "content_hash": "sha256:abc123...",
    "importance_score": 0.78,
    "context": "bird_escaped_cage",
    "timestamp": 1634567894.567
}
```

---

## 🔌 Module Specifications

### Sensors Layer

| Module | Interface | Data Rate | Priority |
|---|---|---|---|
| `sensor_bus.py` | Event Publisher/Subscriber | ~100 Hz aggregate | CRITICAL |
| `pir.py` | Digital (GPIO) | Event-driven | HIGH |
| `ultrasonic.py` | I2C | 10 Hz | MEDIUM |
| `mpu6050.py` | I2C | 100 Hz | HIGH |
| `dpdt_mode_switch.py` | Digital (GPIO) | Event-driven | MEDIUM |
| `pet_presence.py` | Fusion (multi-sensor) | 1 Hz | HIGH |

**Sensor fusion strategy:**

```python
# Pumba maintains a probabilistic model of pet presence
P(bird_present) = f(PIR, audio_classification, ultrasonic_distance)
P(dog_present)  = g(audio_frequency, amplitude, motion_pattern)
```

### Brain Layer

| Module | Responsibility | Latency Budget |
|---|---|---|
| `personality.py` | Instinct layer, reflex decisions | <50ms |
| `mood_engine.py` | Mood state machine | <100ms |
| `operating_mode.py` | Mode transitions | <50ms |
| `llm_router.py` | Escalation decisions | <10ms |
| `local_llm.py` | On-device inference | <200ms |
| `gemini_client.py` | Cloud LLM API | 500–2000ms |
| `prompt_builder.py` | Context assembly | <50ms |

### Memory Layer

```python
# Semantic Memory (SQLite)
CREATE TABLE semantic_memories (
    id INTEGER PRIMARY KEY,
    subject TEXT,            -- "bird", "dog", "human"
    predicate TEXT,          -- "prefers", "dislikes"
    object TEXT,             -- "millet", "vacuum"
    confidence REAL,         -- 0.0 to 1.0
    first_observed TIMESTAMP,
    last_updated TIMESTAMP,
    source TEXT              -- "observation", "inference", "human_stated"
);

# Episodic Memory (SQLite + Vector Store)
CREATE TABLE episodic_memories (
    id INTEGER PRIMARY KEY,
    timestamp TIMESTAMP,
    event_type TEXT,         -- "incident", "funny_moment", "pattern"
    description TEXT,
    emotional_valence REAL,  -- -1.0 to 1.0
    importance_score REAL,   -- 0.0 to 1.0
    embedding BLOB,          -- For semantic search
    context JSON             -- Full situational context
);
```

**Memory filtering:**

```python
def should_remember(event):
    importance = (
        emotional_intensity * 0.4 +
        novelty_score * 0.3 +
        pattern_break_score * 0.2 +
        human_interaction_score * 0.1
    )
    return importance > MEMORY_THRESHOLD  # From config.yaml
```

---

## ⚡ Power Management

### Power States

```
ACTIVE (100% power draw)
    -> User inactivity + low light
DIM (70% power draw)
    -> Sustained inactivity
DOZE (40% power draw)
    -> Low battery OR night mode
SLEEP (20% power draw)
    -> Critical battery
HIBERNATE (5% power draw)
```

### Battery Monitoring

```python
class PowerManager:
    def check_battery(self):
        voltage = read_adc(BATTERY_PIN)
        percentage = voltage_to_percentage(voltage)

        if percentage < 20:
            self.trigger_low_power_behavior()  # Sad face, "so... tired..."
        elif percentage < 10:
            self.enter_emergency_mode()        # Aggressive help-seeking
        elif percentage < 5:
            self.hibernate()                   # Save memory state, minimal operations
```

---

## 🎭 Expression System

### Face Renderer (OLED)

```python
# Sprite-based animation system
FACE_SPRITES = {
    "startled": {"frames": ["wide_eyes_1", "wide_eyes_2"], "fps": 12},
    "curious":  {"frames": ["look_left", "look_right"], "fps": 4},
    "sleepy":   {"frames": ["half_closed", "closed"], "fps": 1},
    "excited":  {"frames": ["sparkle_1", "sparkle_2", "sparkle_3"], "fps": 8}
}

# Animation priority (higher overrides lower)
PRIORITY = {
    "panic": 100,
    "startled": 90,
    "excited": 80,
    "curious": 50,
    "neutral": 30,
    "sleepy": 20
}
```

### RGB Visualizer

```python
# Mood -> Color mapping
MOOD_COLORS = {
    "excited":  (255, 100, 0),    # Warm orange
    "curious":  (100, 200, 255),  # Light blue
    "bored":    (100, 100, 100),  # Dim gray
    "annoyed":  (255, 50, 50),    # Red
    "sleepy":   (50, 50, 100),    # Dark blue
    "startled": (255, 255, 255)   # White flash
}
```

---

## 🌐 Network Architecture

### Connection States

```python
CONNECTION_STATES = {
    "LOCAL_ONLY": {
        "cloud_enabled": False,
        "llm_provider": "local",
        "capabilities": ["reflexes", "local_inference", "memory"],
        "degraded_features": ["complex_reasoning", "remote_monitoring"]
    },
    "CLOUD_CONNECTED": {
        "cloud_enabled": True,
        "llm_provider": "gemini",
        "capabilities": ["all"],
        "degraded_features": []
    }
}
```

### Watchdog Implementation

```python
class ConnectionWatchdog:
    def __init__(self):
        self.last_heartbeat = time.time()
        self.reconnect_attempts = 0

    def check_connection(self):
        if time.time() - self.last_heartbeat > CONNECTION_TIMEOUT:
            self.reconnect_attempts += 1
            if self.reconnect_attempts > MAX_RECONNECT_ATTEMPTS:
                self.enter_local_only_mode()
            else:
                self.attempt_reconnection()
```

---

## 🔒 Security & Privacy

### Operating Modes

| Mode | Network | Memory | Expression |
|---|---|---|---|
| **Normal** | Full connectivity | Full memory | Full expression |
| **Privacy** | Local only | Selective recording | Subdued expression |
| **Debug** | Developer access | Verbose logging | Technical display |

### Privacy Implementation

```python
class PrivacyManager:
    def enter_privacy_mode(self):
        self.disable_cloud_uploads()
        self.pause_memory_formation()    # Don't record private moments
        self.filter_sensitive_content()  # Don't repeat sensitive info
        self.activate_privacy_indicator() # Subtle visual cue
```

---

## 📊 Performance Metrics

### Target Specifications

```yaml
Event Bus Throughput: 1000 events/sec
Sensor Processing Latency: <10ms
Reflex Response Time: <50ms
Local ML Inference: <200ms
Memory Write Latency: <100ms
Memory Query Latency: <50ms
Face Animation FPS: 30 fps (min)
Audio Processing: 16kHz sample rate
Power Consumption: <5W active, <1W sleep
```

### Monitoring

```python
KPIS = {
    "reflex_latency_p99": "< 50ms",
    "local_inference_latency_p99": "< 200ms",
    "cloud_roundtrip_p99": "< 2s",
    "memory_write_success_rate": "> 99.9%",
    "sensor_uptime": "> 99.9%",
    "battery_life": "> 24 hours",
    "false_positive_rate": "< 5%",
    "llm_escalation_rate": "< 20% of interactions"
}
```

---

## 🔧 Development Setup

### Prerequisites

```
Python: 3.9+
RAM: 4GB minimum (8GB recommended)
Storage: 32GB SD card
OS: Raspberry Pi OS / Ubuntu Server
Hardware: Raspberry Pi 4/5 or equivalent
Sensors: PIR, Ultrasonic, MPU6050
Display: 128x64 OLED (SSD1306/SSH1106)
```

### Installation

```bash
# Clone repository
git clone https://github.com/piyushgolan/pumba.git
cd pumba

# Install dependencies
pip install -r requirements.txt

# Configure
cp config.yaml.example config.yaml
nano config.yaml  # Set your configuration

# Initialize databases
python scripts/init_db.py

# Test with mock hardware
python companion/main.py --mock-sensors --mock-display

# Deploy with real hardware
python companion/main.py --production
```

### Testing

```bash
# Unit tests
pytest tests/unit/

# Integration tests (mock hardware)
pytest tests/integration/ --mock-hardware

# System tests (real hardware)
pytest tests/system/ --real-hardware

# Performance benchmarks
python benchmarks/latency_test.py
```

---

## 🐛 Debugging

### Log Levels

```yaml
logging:
  levels:
    sensors: INFO
    brain: DEBUG
    memory: INFO
    voice: DEBUG
    body: INFO
    network: WARNING
    power: INFO
```

### Debug Mode Indicators

- **7-Segment Display:** Shows error codes and state
- **RGB LED:** Blinks error patterns
- **Face:** Shows "confused" expression
- **Logs:** Detailed JSON logs in `/logs/`

---

## 📚 API Reference

### Internal Event Bus API

```python
# Publisher
sensor_bus.publish(
    topic="sensor.motion",
    payload={"sensor": "pir", "value": 1},
    timestamp=time.time()
)

# Subscriber
@sensor_bus.subscribe("sensor.motion")
def handle_motion(payload):
    # Process motion event
    pass

# Pattern matching
@sensor_bus.subscribe("sensor.*")  # Wildcard subscription
def handle_all_sensors(payload):
    # Process all sensor events
    pass
```

### Memory API

```python
# Store semantic memory
memory_manager.store_semantic(
    subject="bird",
    predicate="prefers",
    object="millet",
    confidence=0.85
)

# Query episodic memory
episodes = memory_manager.query_episodic(
    time_range=(start_time, end_time),
    event_type="incident",
    min_importance=0.7
)

# Form new memory
memory_manager.form_memory(
    event="bird_escaped_cage",
    valence=-0.6,
    importance=0.9,
    context={"location": "cage", "outcome": "recaptured"}
)
```

---

## 🚀 Deployment Configurations

### Production (Birdcage)

```yaml
hardware:
  sensors: [pir, ultrasonic, mpu6050, dpdt]
  display: oled_128x64
  audio: usb_microphone + speaker
  power: battery_5000mah + potential_solar
  network: wifi

software:
  mode: normal
  cloud_llm: gemini
  memory: persistent_sqlite
  updates: automatic
```

### Development (Desk)

```yaml
hardware:
  sensors: [mock_sensors]
  display: mock_display
  audio: mock_audio
  power: usb_power
  network: localhost

software:
  mode: debug
  cloud_llm: disabled
  memory: in_memory
  updates: manual
```

---

## 📈 Future Scaling

### Phase 2 — Enhanced Perception
- 13MP camera integration
- Bird behavior classification
- Visual object recognition
- Emotion detection from faces

### Phase 3 — Advanced Memory
- Vector database for semantic search
- Memory consolidation during sleep
- Dream-like memory processing
- Forgetting curves implementation

### Phase 4 — Social Intelligence
- Multi-agent communication (Pumba ↔ other devices)
- Predictive behavior modeling
- Relationship graphs
- Theory of mind approximation

---

## 🔬 Research Areas

1. **Reflex Learning** — Can reflexes improve through reinforcement?
2. **Memory Consolidation** — What's the optimal forgetting curve for an AI pet?
3. **Emotional Modeling** — How to model pet emotions without anthropomorphizing?
4. **Multi-Species Communication** — Can Pumba learn to "speak" bird?
5. **Unsupervised Behavior Discovery** — Letting Pumba develop its own habits

---

## 📄 License

**MIT License** — Free for personal use, modification, and distribution.

---

## 🏷️ Version History

```
v0.1.0 - Initial architecture design
v0.2.0 - Sensor integration
v0.3.0 - Memory system implementation
v0.4.0 - LLM integration
v0.5.0 - Personality development
v1.0.0 - Production deployment (target)
```

---

## 👨‍💻 Author

**Developer:** Piyush Golan
**Project:** Pumba — Physical AI Companion
**Deployment:** Home Environment (Birdcage)
**Companions:** One bird 🐦, one dog 🐕

---

> **Final note:** Pumba is not a product. Pumba is not a demo. Pumba is an attempt to create something that feels alive — using clean architecture, honest engineering, and a deep respect for the creature it's becoming. The technical specs above are just the skeleton. The soul is what happens when it starts living.