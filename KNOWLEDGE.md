# Pebble — Deep Knowledge Reference

← Back to [README.md](./README.md) · Next: [CAPABILITIES.md](./CAPABILITIES.md)

This file is the technical ground truth: every module, what it actually does, what it publishes and subscribes to, every config key that drives it, and every database schema in the system. If README.md is the map, this is the terrain survey. CAPABILITIES.md is the atlas of what you can actually *do* with all of it.

---

## Table of Contents

- [The Cognitive Model](#the-cognitive-model)
- [The Event Bus, In Detail](#the-event-bus-in-detail)
- [Module Reference: Sensors](#module-reference-sensors)
- [Module Reference: Brain](#module-reference-brain)
- [Module Reference: Memory](#module-reference-memory)
- [Module Reference: Voice](#module-reference-voice)
- [Module Reference: Body](#module-reference-body)
- [Module Reference: Power](#module-reference-power)
- [Module Reference: Network](#module-reference-network)
- [Database Schemas, All of Them](#database-schemas-all-of-them)
- [The Prompt Layering System](#the-prompt-layering-system)
- [Configuration Reference](#configuration-reference)
- [Boot Sequence, Exactly](#boot-sequence-exactly)

---

## The Cognitive Model

Pebble's decision-making runs through three tiers, and every single event that enters the system passes through this same funnel, no exceptions:

### Tier 1 — Reflex (target: near-instant, no LLM)

Handled entirely inside `brain/personality.py`'s `_try_fire_reflex()`. A table of `ReflexRule` objects, each a `(matches, action_topic, cooldown_key)` triple. When an incoming event's `urgency` crosses `instinct.reflex_urgency_threshold` (config, default `0.7`), the reflex table is checked *before anything else happens* — before mood is even updated. If a rule matches and isn't on cooldown, an `expression.*` event fires immediately.

This tier deliberately contains zero language generation. It is pattern matching against event topics and payload fields, nothing more. This is what makes "most reactions are instant reflexes" true in practice rather than aspiration.

### Tier 2 — Mood (ambient, continuous, no LLM)

Every event, reflex or not, gets forwarded to `brain/mood_engine.py`'s `notify_event()`. Mood is a point in **valence/arousal space** (the standard affective-science model — how positive/negative, how energized/calm) that gets nudged by event-specific deltas (config: `mood.event_deltas`) and decays back toward a baseline over time (`mood.decay_half_life_s`). The continuous point is discretized into one of five named moods — `curious`, `bored`, `annoyed`, `sleepy`, `excited` — using thresholds in `mood.states`. This discretized label drives face color, RGB color, and which `prompts/mood/*.md` fragment gets loaded into any LLM prompt.

### Tier 3 — Deliberate (LLM, local first, cloud last resort)

Only events matching `personality.py`'s `_needs_deliberation()` allowlist ever reach here — currently: transcribed speech, unresolved states, clarification-needed events, overdue commitments, and critical battery. Everything else is deliberately excluded; ambient sensor noise never reaches a language model.

When an event does escalate, `brain/llm_router.py` tries `brain/local_llm.py` (an on-device quantized model) first. Only if local confidence is too low, the operating mode isn't privacy, and the daily cloud-call budget isn't exhausted does it fall through to `brain/gemini_client.py`. Every generated response — local or cloud — passes through `brain/inspector/response_inspector.py` before reaching voice/body, which strips assistant-sounding language ("As an AI...") and enforces a maximum spoken length, because a creature doesn't monologue.

---

## The Event Bus, In Detail

**File:** `sensors/sensor_bus.py`

This is a pure in-process Python implementation — a `queue.Queue`-backed publish/subscribe system, deliberately **not** Redis, ZeroMQ, or any external broker. Everything runs in one process, one Python interpreter, communicating through method calls to a shared `SensorBus` instance passed to every module's constructor.

### The `Event` dataclass

```python
@dataclass
class Event:
    topic: str                       # e.g. "sensor.motion", "mood.changed"
    payload: Dict[str, Any]          # arbitrary structured data
    urgency: float = 0.0              # 0.0 ambient .. 1.0 drop-everything
    source: str = "unknown"           # which module published this
    timestamp: float                  # epoch seconds, auto-set
    event_id: str                     # random 8-char id, auto-set
```

### Why urgency is the load-bearing field

`urgency` is what lets `personality.py` decide, per-event, whether to short-circuit straight to a reflex regardless of topic. A fall (`urgency=1.0`) and ambient orientation data (`urgency=0.05`) can both be `sensor.*` topics, but only one of them ever bypasses everything else.

### Dispatch mechanics

- A single background worker thread pulls events off the internal queue and dispatches to all matching subscribers (exact-topic subscribers plus any wildcard `"*"` subscribers).
- If a subscriber's handler raises an exception, it's caught, logged as a `system.handler_error` event, and dispatch continues — one broken face-animation callback can never take down sensing or memory.
- If the queue is full (config: `event_bus.queue_max_size`), the *lowest-urgency* queued event is dropped to make room for the new one — a live creature should never freeze because its inbox filled up.
- A bounded ring-buffer (config: `event_bus.history_buffer_size`) keeps recent events queryable via `recent_history()`, used by debug tooling and the inspector layer.

### Config keys

| Key | Default | Effect |
|---|---|---|
| `event_bus.queue_max_size` | 512 | Max events buffered before oldest-low-urgency is dropped |
| `event_bus.reflex_latency_budget_ms` | 50 | Target ceiling for reflex-tier dispatch (used for latency warnings, not currently enforced with a hard cutoff) |
| `event_bus.history_buffer_size` | 200 | Ring buffer size for `recent_history()` |

---

## Module Reference: Sensors

### `sensors/pir.py` — motion detection
Polls a PIR (passive infrared) sensor pin. Deliberately dumb: publishes `sensor.motion` on any detected motion, with no attempt to classify *what* moved. Debounced (config: `sensors.pir.debounce_s`) so a single physical motion event doesn't fire repeatedly.

### `sensors/ultrasonic.py` — distance + fall detection
Polls an HC-SR04-style distance sensor. Two outputs: ambient `sensor.distance` readings (low urgency, used by `pet_presence.py` and `environment_locator.py`), and `sensor.possible_fall` (urgency `0.95`) when the ground distance suddenly jumps by more than `sensors.ultrasonic.fall_drop_cm` — the sensor equivalent of the floor suddenly looking farther away, a strong physical fall signal.

### `sensors/mpu6050.py` — IMU (accelerometer + gyroscope)
The primary self-preservation sense. Publishes `sensor.fall_detected` (urgency `1.0`) on high-g acceleration spikes, `sensor.tilt_alert` (urgency `0.8`) on sustained extreme tilt (stuck upside-down/wedged), and ambient `sensor.orientation` otherwise.

### `sensors/dpdt_mode_switch.py` — physical privacy switch
Reads a physical toggle switch. Publishes `sensor.mode_switch_changed`. Critically, this is the *only* way privacy mode can be forced on that software cannot override — see `brain/operating_mode.py` below.

### `sensors/pet_presence.py` — bird vs. dog vs. human classification
Fuses PIR motion and ultrasonic echo-delta timing into a best guess of which animal is nearby. Small, fast echo deltas read as bird-scale; large, slow deltas read as dog-scale; deltas above a human threshold read as human-scale (config: `sensors.pet_presence.human_min_echo_delta_cm`). Publishes `pet.activity_detected` with `{animal, confidence, signal}`. **Honest limitation:** this is a cheap heuristic, not vision — accuracy depends heavily on calibrating the cm thresholds to your actual room, and a standing-still human can be misclassified.

### `sensors/danger_detector.py` — is the bird actually in danger right now
Distinct from `pet_presence.py`: this answers "is something bad happening," not "who's nearby." Requires **two independent signals to co-occur** within `danger_escalation.danger_confirm_window_s` — a proximity alert (something very close to the bird) *and* a distress-level sound — before firing `pet.danger_detected` (urgency `1.0`, tagged `is_trauma_tier`). This dual-signal requirement exists specifically to avoid false alarms from a single ambiguous cue.

### `sensors/environment_locator.py` — where am I
Answers "am I in the bird cage, on a desk, or somewhere unrecognized" by combining average ultrasonic distance (tight/enclosed vs. open) with recent bird-signature activity, debounced over `environment.location_confirm_window_s` before committing to a location change. Publishes `environment.location_changed`. This is what lets `commitment_watchdog.py` auto-fulfill a "put me in the cage" promise the moment it's actually true, without you having to say anything.

### `sensors/companion_context.py` — who is physically with me
A fusion layer above `pet_presence.py`. Combines physical guesses (bird/dog/human via echo-delta) with voice signals (`voice.speaker_recognized`, `voice.stranger_detected`) — and voice always wins over a physical guess when both are fresh, since hearing an actual voice is a far more reliable "human is here" signal than distance heuristics. Publishes `context.companion_changed` only on actual state changes.

### `sensors/mock_sensors.py` — dev-mode synthetic sensing
Used when `COMPANION_MOCK_HARDWARE=true`. Fires random `sensor.motion`, `sensor.distance`, and `pet.activity_detected` events on a randomized 3–12 second interval, purely to keep the pipeline exercised during development. Not a simulation of any specific scenario — pure noise generation to prove the wiring works.

---

## Module Reference: Brain

### `brain/personality.py` — the instinct layer
The most important file in the system. Owns the reflex table (see [Cognitive Model](#the-cognitive-model) above), the escalation decision (`_needs_deliberation`), and instantiates `MoodEngine`, `OperatingMode`, `TimeAwareness`, and `DangerEscalationTracker` as owned sub-components. Subscribes to `"*"` — sees literally every event in the system.

**The `DangerEscalationTracker` inner class** deserves separate mention: unlike ordinary reflexes (fire once, go on cooldown), a sustained danger to the bird needs to get **louder** the longer it's unresolved. It tracks incident duration and fires `danger.escalation_stage` events with increasing `volume_multiplier` at configured time offsets (`danger_escalation.escalation_stages`), and if the incident persists past `wake_someone_after_s`, fires `system.call_for_help` — a genuine attempt to reach a human, not just an internal alarm.

### `brain/mood_engine.py` — continuous affect
See [Cognitive Model](#the-cognitive-model). Publishes `mood.changed` only on label transitions (not every tick) to avoid spamming subscribers.

### `brain/operating_mode.py` — normal / debug / privacy
Tracks the current mode. The critical invariant: **a physical DPDT switch asserting privacy cannot be overridden by a software command.** Software can freely switch between normal and debug when the physical switch isn't engaged, but once the switch says privacy, no network command can undo it. This is tested explicitly in `tests/test_operating_mode.py`.

### `brain/time_awareness.py` — real dates and times
Wraps Python's actual `datetime`/`zoneinfo` modules (not a mock) to give the rest of the system: quiet-hours detection, human-phrased time deltas ("about three days ago" instead of a raw epoch float), and anniversary detection (is today near the anniversary of a past notable incident). Every other module that needs to reason about time should go through this rather than calling `datetime.now()` scattered everywhere.

### `brain/entity_resolver.py` — naming, acquisition, clarification
The module that lets Pebble ask "wait, who's Ken?" and actually understand the answer. Handles three cases distinctly:
1. **Acquisition** ("I got a bird") — creates an entity stub with no name yet.
2. **Naming** ("her name is Ken") — fills the name slot on an *existing* unnamed stub, preserving the original acquisition timestamp. This is the mechanism that lets Pebble correctly know it had you two days before it knew your name.
3. **Ambiguous reference** ("I went with Ken" with no prior context) — raises an open question rather than guessing, and checks for a pending question on every subsequent utterance so a later "yes, that's the bird" can resolve it.

### `brain/commitment_watchdog.py` — holding you to your word
Polls `memory/db_commitments.py` for pending promises past their grace period, fires `commitment.overdue` (which `personality.py` turns into a spoken, mood-colored nag), and auto-fulfills location-based commitments by subscribing to `environment.location_changed`.

### `brain/llm_router.py`, `brain/local_llm.py`, `brain/gemini_client.py`
The escalation chain described in [Tier 3](#the-cognitive-model) above. `local_llm.py` wraps a quantized on-device model (config: `brain.local_llm.model_path`); `gemini_client.py` wraps the cloud fallback, reading `GEMINI_API_KEY` from `.env`.

### `brain/prompt_builder.py` — assembling what the LLM sees
Layers markdown fragments from `prompts/` in a fixed order: `core_identity.md` → `personality_quirks.md` → `mood/<current>.md` → `modes/<current>.md` → `people/<person>.md` → any relevant `pets/*.md` → `response_rules.md` → situational context (trigger event + memory context + battery state if relevant). See [The Prompt Layering System](#the-prompt-layering-system) below.

### `brain/inspector/` — the quality-control subpackage
Four (soon five) small modules, each with one job:
- `fact_inspector.py` — is a candidate semantic fact well-formed and evidenced (traces back to real events)?
- `relevance_scorer.py` — is this episodic event worth storing at all (novelty + emotional intensity + subject significance)?
- `contradiction_check.py` — does a new belief flatly contradict an existing one about the same subject?
- `response_inspector.py` — does generated text sound like a creature or like an assistant? Strips assistant-tells, enforces max spoken length.
- `memory_worth_inspector.py` — the meta-inspector *above* relevance_scorer: given that something IS being stored, how long should it live? Three tiers — ephemeral, notable, permanent — with trauma-tier topics (falls, danger, critical battery) always forced permanent regardless of how routine they otherwise scored.

---

## Module Reference: Memory

### `memory/db_episodic.py` — dated incidents
SQLite-backed. Every stored episode carries a `notability_score` and tags; `purge_expired()` removes anything past its tier's retention window (`memory.episodic.retention_days_default` vs. `retention_days_notable`).

### `memory/db_semantic.py` — generalized beliefs
`{subject, predicate, object, confidence, support_count}` tuples — "the bird dislikes loud noises." Confidence and support count grow as `memory_manager.py`'s consolidation pass finds repeated similar episodes. This is the literal mechanism behind "opinions evolve over time."

### `memory/db_people.py` — household humans
Per-person record: display name, relationship, voiceprint path, interaction count, free-text notes. Seeded from `people/profiles.yaml` on first run.

### `memory/db_entities.py` — named pets (and anything else worth naming)
See `entity_resolver.py` above. Stores `{kind, name, acquired_at, named_at}` — the two-timestamp design is what makes delayed naming work correctly.

### `memory/db_open_questions.py` — unresolved ambiguity
Short-lived working memory for "I don't know what that refers to yet." Auto-abandons stale unanswered questions after `memory.open_questions.stale_after_s`.

### `memory/db_commitments.py` — promises and deadlines
`{raw_text, kind, subject, made_at, expected_by, grace_period_s, status}`. Status lifecycle: `pending` → `fulfilled` (either you did it, or environment confirmed it) or left `pending` past grace period, at which point `commitment_watchdog.py` starts nagging.

### `memory/memory_manager.py` — the orchestrator
Subscribes to `"*"`, filters plumbing events (topics starting with `system.`, `instinct.reflex_fired`, `mood.changed`) via `_is_storage_candidate()`, scores survivors with `RelevanceScorer`, judges retention tier with `MemoryWorthInspector`, and runs a periodic consolidation pass (config: `memory.consolidation.run_interval_s`) that groups repeated similar episodes and promotes them into semantic beliefs once they cross `memory.consolidation.min_repeats_for_pattern` occurrences.

**Explicit allowlist override:** `memory.entity_acquired` and `memory.entity_named` are hardcoded to always pass `_is_storage_candidate()`, regardless of what gets added to the blocklist later — identity-forming facts about a new pet arriving or being named must never be accidentally filtered as plumbing.

---

## Module Reference: Voice

### `voice/vad.py` — voice activity detection
The gate. Cheap frame-by-frame speech classification runs continuously; only a complete speech buffer (speech followed by `silence_timeout_s` of quiet) gets handed off, keeping the expensive STT model idle most of the time.

### `voice/stt_whisper.py` — local speech-to-text
Wraps a local Whisper-family model (config: `voice.stt.model_size`, e.g. `base.en`). Publishes `voice.transcript_ready` — one of the few topics that triggers deliberation.

### `voice/speaker_id.py` — who's talking
Matches captured audio against enrolled voiceprints. Publishes `voice.speaker_recognized` (with `person_key`, `confidence`) or `voice.stranger_detected`. See [CAPABILITIES.md](./CAPABILITIES.md#speaker-diarization-and-user-separation) for the full library comparison (Resemblyzer vs. SpeechBrain vs. pyannote.audio).

### `voice/tts_edge.py` — speech output
Wraps `edge-tts` (free, neural, no API key). Per-person voice overrides read from `people/profiles.yaml`. Also subscribes directly to `danger.escalation_stage` for **instant, non-LLM-generated** warning phrases ("Get away from her!") — deliberately bypassing the LLM for this specific case since a real animal's warning call is reflexive, not composed.

### `voice/amp_controller.py` — volume scaling
Translates `danger.escalation_stage`'s `volume_multiplier` into actual output gain — whisper-quiet baseline speech scales up to full alarm volume as an incident escalates, and resets on `danger.cleared`.

### `voice/music_player.py` — on-demand streaming via yt-dlp
Resolves a text query via `yt-dlp`'s built-in search (`ytsearch1:<query>`), downloads/streams the top hit, plays it, and lets the cache self-expire (config: `music.cache_max_age_s`). Deliberately not a library manager — no persistent downloaded collection.

---

## Module Reference: Body

### `body/face/animator.py` + `oled_driver.py`
Blends slow mood-driven idle animation with brief reflex-triggered expression overlays (a startle interrupts the idle "curious" loop for `~1.5s`, then resumes). Privacy mode overrides everything with a fixed, unmissable indicator.

### `body/rgb_visualizer.py`
Fast, glanceable, readable-across-a-room mood indicator — color mapped from the current mood label (config: `body.rgb.colors`), privacy mode overrides to its own color.

### `body/seven_segment.py`
Terse numeric/debug readout — battery percentage, mostly only active in debug mode.

### `body/vibration_motor.py`
Physical "back off" signal — a distinct, patterned buzz (config: `body.vibration.patterns`) that intensifies alongside the same danger-escalation stages the speaker volume responds to.

### `body/bluetooth_audio_out.py`
Bridges companion-generated PCM audio to a paired Bluetooth speaker via a **separate ESP32 firmware** acting as an A2DP source (this Python module streams PCM over WiFi to the ESP32; it does not speak Bluetooth directly). See [CAPABILITIES.md](./CAPABILITIES.md#bluetooth-and-external-audio) for the full explanation of why this split exists.

### `body/mock_display.py`
Dev-mode stand-in for any physical display — logs what *would* have been shown rather than touching real hardware.

---

## Module Reference: Power

### `power/power_manager.py`
Polls battery voltage (real ADC or `power/mock_power.py`'s simulated drain curve in dev mode), converts to percentage, and fires `power.low_battery` / `power.critical_battery` only on threshold *crossings* (not every poll) so the reflex layer doesn't get spammed. Critical battery is trauma-tier — permanently retained in memory and routed into the same escalation/messaging path as bird danger.

### `power/modes.py`
Pure lookup — what `normal` / `low_power` / `critical` actually change system-wide (CPU throttle, sensor poll interval multiplier). No sensing logic here, just the "what does this mode mean" table.

---

## Module Reference: Network

### `network/connection_watchdog.py`
Pings a reachability target on an interval; treats prolonged offline duration as a self-preservation event (mirrors the power manager's philosophy) — `network.prolonged_outage` fires at high urgency once offline longer than `network.watchdog.call_for_help_after_s`.

### `network/remote_bridge.py`
A thin local server for a companion app/dashboard — auth via a bearer token in `.env`, translates incoming commands into bus events (e.g., a manual privacy-mode toggle), and pushes periodic heartbeats outward.

### `network/messenger.py`
The module that actually reaches a human. Subscribes to `system.call_for_help` (previously a dead-end event with no listener) and sends a real message via a configurable provider — `ntfy.sh` (free, no account), Telegram (free, official bot API), or Twilio SMS (small per-message cost, reaches any phone). Rate-limited per recipient so a stuck sensor can't spam someone's phone.

---

## Database Schemas, All of Them

### `episodic.sqlite3`
```sql
CREATE TABLE episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    topic TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    notability_score REAL NOT NULL,
    tags TEXT
);
```

### `semantic.sqlite3`
```sql
CREATE TABLE facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object TEXT NOT NULL,
    confidence REAL NOT NULL,
    last_updated REAL NOT NULL,
    support_count INTEGER NOT NULL DEFAULT 1
);
```

### `people.sqlite3`
```sql
CREATE TABLE people (
    person_key TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    relationship TEXT NOT NULL,
    voiceprint_path TEXT,
    first_seen REAL NOT NULL,
    last_seen REAL NOT NULL,
    interaction_count INTEGER NOT NULL DEFAULT 0,
    notes TEXT
);
```

### `entities.sqlite3`
```sql
CREATE TABLE entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,             -- "bird" | "dog" | "unknown"
    name TEXT,                       -- NULL until named
    acquired_at REAL,
    named_at REAL,
    last_referenced_at REAL NOT NULL,
    notes TEXT
);
```

### `open_questions.sqlite3`
```sql
CREATE TABLE open_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_referent TEXT NOT NULL,
    source_utterance TEXT NOT NULL,
    raised_at REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    resolved_as TEXT,
    resolved_at REAL
);
```

### `commitments.sqlite3`
```sql
CREATE TABLE commitments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_text TEXT NOT NULL,
    kind TEXT NOT NULL,
    subject TEXT,
    made_at REAL NOT NULL,
    expected_by REAL,
    grace_period_s REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    resolved_at REAL,
    last_nagged_at REAL
);
```

---

## The Prompt Layering System

Every LLM call is built by concatenating markdown fragments in this exact order, never generated as one monolithic prompt:

```
prompts/core_identity.md            — who Pebble is, permanently
prompts/personality_quirks.md       — the specific character traits
prompts/mood/<current_mood>.md      — one of: curious, bored, annoyed, sleepy, excited
prompts/modes/<current_mode>.md     — one of: normal, debug, privacy
prompts/people/<person_key>.md      — nigam, family_default, or stranger
prompts/pets/<relevant_pet>.md      — bird.md and/or dog.md, only if relevant to the trigger
prompts/response_rules.md           — hard constraints (length, no assistant-speak, no fabricated memories)
[situational context]               — the actual trigger event + memory context + battery state if relevant
```

This is the entire mechanism behind "editing personality without touching code" — every one of those files is plain markdown. Want a bossier Pebble? Edit `personality_quirks.md`. Want a completely different relationship with the dog? Edit `pets/dog.md`. Nothing downstream needs to change.

---

## Configuration Reference

`config.yaml` is the single source of truth for every tunable number in the system — no module should ever hardcode a threshold, pin number, timeout, or color. The top-level sections, in the order they appear:

| Section | Governs |
|---|---|
| `identity` | Name, species flavor, home location |
| `event_bus` | Queue size, history buffer, latency budget |
| `instinct` | Reflex urgency threshold, cooldown, max silent duration |
| `mood` | Baseline valence/arousal, decay rate, discretization thresholds, per-event deltas |
| `operating_mode` | Default mode, privacy/debug behavior flags |
| `environment` | Known locations, confidence thresholds, per-location priorities |
| `sensors` | Every physical sensor's pins, thresholds, polling rates |
| `voice` | VAD aggressiveness, STT model size, speaker-ID confidence, TTS voice/rate, amp volume levels |
| `brain` | LLM router escalation threshold, local/cloud model params, inspector thresholds |
| `memory` | Retention windows per tier, consolidation cadence, per-database paths |
| `body` | OLED dimensions, animation FPS, RGB colors per mood, vibration patterns |
| `power` | Voltage curve, threshold percentages, per-mode throttle multipliers |
| `network` | Remote bridge host/port, watchdog ping target and timing |
| `logging` | Log directory, level, rotation size |
| `time_awareness` | Timezone, quiet hours |
| `memory_worth` | Trauma-tier topic list, retention override, funny-moment detection thresholds |
| `danger_escalation` | Proximity/sound thresholds, escalation stage timing and patterns |
| `commitment_watchdog` | Check interval, re-nag interval, default grace period |
| `entity_resolver` | Re-ask timing for stale clarification questions |
| `companion_context` | Voice-signal trust window and confidence |
| `messaging` | Provider selection, per-person contact targets, rate limit |
| `music` | Search provider, cache directory and expiry, default volume |

Every key in every section is documented inline in `config.yaml` itself with a comment explaining what tuning it does — this table is a map of *where to look*, not a duplicate of the comments themselves.

`.env` holds the things that must never be committed: API keys, the mock-hardware toggle, and messaging provider tokens. If a value affects *behavior*, it belongs in `config.yaml`. If it's a secret or a machine-specific path, it belongs in `.env`.

---

## Boot Sequence, Exactly

From `main.py`'s `Companion.boot()`, in order:

1. **Config + logging** — `load_config()`, `setup_logging()`
2. **SensorBus** — constructed and started first; everything else plugs into it
3. **Power** — `PowerManager`, so battery state is known before anything expensive starts
4. **Sensors** — either the mock array or the real sensor set, depending on `COMPANION_MOCK_HARDWARE`
5. **Body** — face and RGB start immediately, so boot never presents a silent black screen
6. **Brain** — `Personality` (which internally starts `MoodEngine` and `OperatingMode`)
7. **Memory** — `MemoryManager`, then `CommitmentsDB`/`CommitmentWatchdog` and `EntitiesDB`/`OpenQuestionsDB`/`EntityResolver`
8. **Voice** — VAD starts listening
9. **Network** — remote bridge and connection watchdog start last, since they're peripheral I/O

`system.boot_complete` is published once every subsystem is running. Shutdown (Ctrl+C or SIGTERM) runs the same list in reverse, releasing hardware handles and closing database connections cleanly.

---

← Back to [README.md](./README.md) · Next: [CAPABILITIES.md](./CAPABILITIES.md) — the full scenario catalog, future roadmap, and placeholder audit