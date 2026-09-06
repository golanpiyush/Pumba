# Pebble — Full Capability Catalog

← Back to [README.md](./README.md) · [KNOWLEDGE.md](./KNOWLEDGE.md)

This is the exhaustive reference. Everything Pebble is designed to do, organized as concrete scenarios rather than abstract feature bullets, because "handles bird safety" means nothing until you can picture the actual moment it happens. Every scenario below is tagged:

- **LIVE** — real, tested code, works today (with or without real hardware attached)
- **STUB** — the event flow and module exist; a `# SENSOR INPUT HOOK` marks exactly where real hardware/API code needs to go
- **DESIGNED** — architecturally planned and described here in full, but no code exists yet

Nothing in this document claims more than what's true. If you build toward a DESIGNED scenario and get stuck, the corresponding module names are given so you know exactly where in the codebase it belongs.

After the scenario catalog: the 35 future feature ideas, the full speaker-separation research and recommendation, the Bluetooth/external-audio explanation, and — at the very end — the complete file-by-file placeholder audit: every line in the codebase that currently returns a stub value and needs real code before this runs on real hardware.

---

## Table of Contents

1. [Self-preservation and physical safety](#1-self-preservation-and-physical-safety)
2. [The bird relationship](#2-the-bird-relationship)
3. [The dog relationship](#3-the-dog-relationship)
4. [Recognizing and treating people differently](#4-recognizing-and-treating-people-differently)
5. [Environment awareness — knowing where it is](#5-environment-awareness--knowing-where-it-is)
6. [Memory — what it keeps, what it forgets, and why](#6-memory--what-it-keeps-what-it-forgets-and-why)
7. [Growth over time — opinions that evolve](#7-growth-over-time--opinions-that-evolve)
8. [Commitments — holding you to your word](#8-commitments--holding-you-to-your-word)
9. [Naming, entities, and asking clarifying questions](#9-naming-entities-and-asking-clarifying-questions)
10. [Mood and personality expression](#10-mood-and-personality-expression)
11. [Privacy and operating modes](#11-privacy-and-operating-modes)
12. [Power and self-monitoring](#12-power-and-self-monitoring)
13. [Network resilience and calling for help](#13-network-resilience-and-calling-for-help)
14. [Voice, speech, and conversation](#14-voice-speech-and-conversation)
15. [Music and audio](#15-music-and-audio)
16. [Messaging real humans](#16-messaging-real-humans)
17. [Physical expression — face, light, sound, touch](#17-physical-expression--face-light-sound-touch)
18. [The 35 future ideas](#18-the-35-future-ideas)
19. [Speaker diarization and user separation](#speaker-diarization-and-user-separation)
20. [Bluetooth and external audio](#bluetooth-and-external-audio)
21. [Placeholder and stub audit](#placeholder-and-stub-audit)

---

## 1. Self-preservation and physical safety

### Scenario 1.1 — A genuine fall **[LIVE — reflex layer / STUB — real IMU read]**
The IMU (`sensors/mpu6050.py`) detects acceleration crossing `sensors.mpu6050.fall_accel_threshold_g`. This publishes `sensor.fall_detected` at urgency `1.0`. `personality.py`'s reflex table matches it in well under a millisecond of Python execution time and fires `expression.startled` — no mood computation, no LLM, nothing standing between sensing and reacting. The face shows a startled expression immediately. Separately, this same event is trauma-tier in `memory_worth_inspector.py`, so it's retained permanently, not aged out like routine noise.

### Scenario 1.2 — A near-fall that isn't confirmed by the IMU **[LIVE / STUB real read]**
The ultrasonic sensor alone can catch a fall the IMU might miss — if the ground distance suddenly jumps (`sensors.ultrasonic.fall_drop_cm`), that's `sensor.possible_fall`, also urgency `0.95`, also wired to the same `expression.startled` reflex. Two independent sensors both watching for the same physical event, neither depending on the other.

### Scenario 1.3 — Being picked up gently vs. actually falling **[DESIGNED]**
Currently, `mpu6050.py`'s stub doesn't distinguish acceleration *profile* — a real fall is a sharp, brief spike; being lifted affectionately is a smoother, sustained acceleration change over a longer window. The real IMU-read implementation should classify by profile shape, not just peak magnitude, so it doesn't startle every time someone picks it up to move it.

### Scenario 1.4 — Being wedged or stuck upside-down **[LIVE / STUB real read]**
Sustained extreme tilt (`sensors.mpu6050.tilt_alert_deg`) fires `sensor.tilt_alert` at urgency `0.8` — distinct from a fall because the physical situation is different (stuck, not falling), even though both come from the same sensor.

### Scenario 1.5 — Critical battery with nobody around **[LIVE reflex / STUB volume+vibration hookup]**
Battery crosses `power.critical_battery_pct` → `power.critical_battery` fires at urgency `1.0` → reflex table fires `expression.panicked_low_power` immediately → the event also escalates to the LLM (it's in `personality.py`'s `_needs_deliberation` allowlist) with the real percentage in context, so any spoken line is grounded in truth, not invented → if the amp/vibration escalation hookup is wired (see [placeholder audit](#placeholder-and-stub-audit)), volume and vibration intensity ramp up the same way bird-danger does, staged over time rather than a single cry then silence.

### Scenario 1.6 — Critical battery escalating to actually reaching you **[DESIGNED — network/messenger.py exists, needs live provider code]**
If nobody responds to the audible/visible distress within the incident, `system.call_for_help` fires with the reason and priority target list (config: `danger_escalation.call_target_priority`). `network/messenger.py` subscribes to this and attempts delivery via whichever provider is configured — ntfy.sh, Telegram, or Twilio SMS — so "calls for help" means an actual notification reaching your phone, not just a louder speaker in an empty room.

### Scenario 1.7 — Prolonged network outage **[LIVE]**
`network/connection_watchdog.py` pings a reachability target on an interval; if offline longer than `network.watchdog.call_for_help_after_s`, fires `network.prolonged_outage` at urgency `0.9`. This is deliberately treated with the same seriousness as a physical danger — a companion that can't reach the outside world for help is itself a form of vulnerability worth flagging.

### Scenario 1.8 — The system clock looks frozen or wrong **[LIVE — `TimeAwareness.clock_looks_stale()`]**
On hardware with no RTC battery and no reliable NTP sync, the system clock can silently freeze or drift. `brain/time_awareness.py`'s `clock_looks_stale()` detects this by checking whether `now()` has actually advanced since it was last observed, past `time_awareness.stale_clock_warn_after_s`. This matters because a frozen clock would silently corrupt every timestamp-dependent feature — commitment deadlines, memory dating, quiet hours — without any obvious symptom otherwise.

### Scenario 1.9 — A handler inside the system misbehaves **[LIVE]**
If any subscriber callback raises an exception mid-dispatch — a bug in a face animation, a malformed sensor payload — `sensor_bus.py` catches it, logs a `system.handler_error` event, and continues dispatching to every other subscriber. One broken module can never cascade into a total failure of sensing, memory, or reflexes.

### Scenario 1.10 — Being physically restrained or blocked from normal orientation **[DESIGNED]**
An extension of tilt detection: if `sensor.tilt_alert` persists for an unusually long duration (not just a momentary tilt but a sustained one, minutes rather than seconds), that's architecturally distinguishable from "briefly bumped" and could warrant its own escalation tier, similar to how danger escalation works for the bird. Would live in `personality.py`'s reflex table as a duration-aware variant of the existing tilt rule.

---

## 2. The bird relationship

### Scenario 2.1 — Noticing the bird is active **[LIVE reflex / STUB real classification]**
`pet_presence.py` classifies a small, fast echo-delta pattern as bird-scale motion, publishes `pet.activity_detected` with `animal: "bird"`. The reflex table's `watch_bird_activity` rule fires `expression.watch_bird` — an attentive, not alarmed, reaction. This is the default good-news case: the bird is just being a bird.

### Scenario 2.2 — The bird chewing something dangerous **[DESIGNED — needs a specific danger classification path]**
Distinct from generic "bird is active": if proximity data suggests the bird is at a fixed, close position near a known-dangerous zone (a wire, an unsafe object) for a sustained duration, that's a different scenario than routine movement. Currently, `danger_detector.py`'s dual-signal requirement (proximity + distress sound) is tuned for *external* threats approaching the bird, not the bird investigating something dangerous on its own. A distinct rule — sustained proximity to a tagged "danger zone" location, independent of sound — would need to be added, most naturally as an extension of `environment_locator.py`'s zone concept (see idea #1 in the future list).

### Scenario 2.3 — The bird is in active danger (something approaching fast, distress sound) **[LIVE full escalation chain / STUB real sensor reads]**
This is the fullest example of the whole architecture working together. `danger_detector.py` requires proximity AND distress-sound signals to co-occur within `danger_escalation.danger_confirm_window_s`. Once both fire, `pet.danger_detected` (urgency `1.0`, trauma-tier) triggers `DangerEscalationTracker` inside `personality.py`, which:
- Immediately fires stage 1 (`chirp_alert`, normal volume, brief vibration)
- If unresolved after `escalation_stages[1].after_s` (default 8s), escalates to stage 2 (`loud_distress`, higher volume, more insistent vibration)
- If still unresolved after `escalation_stages[2].after_s` (default 20s), escalates to stage 3 (`sos_loop`, full volume, urgent vibration pattern)
- If unresolved past `wake_someone_after_s` (default 25s), fires `system.call_for_help` — a real attempt to reach you
- `tts_edge.py` bypasses the LLM entirely for the spoken warning at each stage — a fixed phrase bank ("Get away from her!", "STOP! Away! Away now!") because a real animal's alarm call is reflexive, not composed
- The moment both signals stop, `danger.cleared` fires, everything resets to baseline

### Scenario 2.4 — The bird has been unusually quiet during its normally active hours **[DESIGNED]**
Combining `environment_locator.py`'s presence tracking with `time_awareness.py`'s knowledge of what time it is: if the bird's typical active-hours pattern (learned from accumulated episodic data) shows a gap unusually longer than normal, that's worth a distinct "worry" reaction — genuinely different in character from low arousal/boredom. This is TOP-20-style idea #18 from earlier design passes, not yet implemented.

### Scenario 2.5 — Forming an opinion about a bird habit **[LIVE — consolidation pipeline]**
`memory_manager.py`'s `_run_consolidation_pass()` groups episodic events by `{animal}:{topic}` pattern keys. Once the same pattern (say, `bird:pet.activity_detected` correlating with a particular time of day) recurs at least `memory.consolidation.min_repeats_for_pattern` times, it's promoted into a semantic belief via `db_semantic.py`'s `upsert_fact()` — confidence grows with each additional occurrence. This is the actual mechanism, not a metaphor, behind "opinions about the bird evolve."

### Scenario 2.6 — Referencing a specific past bird incident naturally in conversation **[LIVE mechanism / STUB natural phrasing depends on filled-in LLM]**
When an LLM call is escalated, `prompt_builder.py` includes `memory_context` — real retrieved episodic/semantic data, humanized via `time_awareness.humanize_past_timestamp()` ("about two weeks ago" rather than a raw epoch). The prompt explicitly instructs (`response_rules.md`) never to fabricate a memory that wasn't actually retrieved — if nothing relevant surfaced, the honest in-character answer is "first I'm hearing of it," not an invented anecdote.

### Scenario 2.7 — The bird's name is used correctly regardless of when it was learned **[LIVE]**
See [Section 9](#9-naming-entities-and-asking-clarifying-questions) in full — this is `entity_resolver.py`'s core mechanism.

### Scenario 2.8 — A second bird arrives later **[DESIGNED — flagged gap]**
Currently, `entity_resolver.py`'s naming logic finds "the most recent unnamed stub of a given kind." If you say "I got a bird" a second time while an earlier bird is already named, the resolver correctly creates a new stub (each acquisition creates a fresh entity). But if you got a *second* bird before naming the *first*, the current logic would find one unnamed stub and could misattribute a name meant for the second bird to the first. A real fix needs explicit "another/second/new" language detection — noted as future work, not yet built.

### Scenario 2.9 — Correcting a wrong guess about the bird **[DESIGNED]**
If Pebble assumes a spoken name attaches to the bird but it was actually meant for the dog, there's currently no "no, that's the dog" correction path — a fresh statement like this would just raise a new ambiguous question rather than correcting the prior misattribution. Needs a short-lived "last resolved entity" pointer, described in the future ideas list.

### Scenario 2.10 — The bird's routine forming the basis of a weekly summary **[DESIGNED]**
Using the local LLM (cheap, no cloud call needed) to periodically summarize recent bird-tagged episodic memories into a natural "how's the bird been" narrative on request — genuinely useful, architecturally straightforward (just a scheduled local_llm.py call over filtered `db_episodic.py` results), not yet built as a standing feature.

---

## 3. The dog relationship

### Scenario 3.1 — Noticing the dog, distinctly from the bird **[LIVE reflex / STUB real classification]**
`pet_presence.py`'s echo-delta heuristic classifies large, slow motion as dog-scale (config: `sensors.pet_presence.dog_min_echo_delta_cm`). The reflex table's `cautious_on_dog_activity` rule fires `expression.acknowledge_dog` — a different expression than the bird gets, reflecting a genuinely different instinct: acknowledgment and light caution rather than attentive fondness.

### Scenario 3.2 — The dog getting close to the cage **[LIVE via danger_detector's proximity signal]**
Proximity alone (without a distress sound) doesn't trigger full danger escalation — that requires the dual-signal confirmation. But `sensor.close_proximity_warning` (a lighter-weight, earlier signal — see [vibration_motor.py](#17-physical-expression--face-light-sound-touch)) can fire on proximity alone, triggering a brief physical "get back" buzz well before the stricter danger-detection threshold is crossed. This is a graduated response: mild proximity gets a small physical nudge, confirmed danger gets the full escalation chain.

### Scenario 3.3 — The dog and bird both active at once **[LIVE — both reflexes can fire independently]**
Nothing in the reflex table treats these as mutually exclusive. `watch_bird_activity` and `cautious_on_dog_activity` both have independent cooldown keys, so both can fire in the same short window if both animals are genuinely active — the expression layer would show whichever fired most recently, with the underlying mood engine receiving nudges from both.

### Scenario 3.4 — Forming a slower, more cautious opinion about the dog than the bird **[DESIGNED]**
A deliberate asymmetry worth building: dog-related semantic facts should require *more* repeated evidence than bird-related facts before consolidating into a confident belief, since dog encounters are inherently noisier/less consistent in a shared household than the bird's fixed-location routine. This would be a per-subject override on `memory.consolidation.min_repeats_for_pattern` rather than one global threshold — not yet implemented, but the schema supports it without any structural change.

### Scenario 3.5 — Tattling on the dog when you're nearby **[DESIGNED]**
If the dog does something near the cage while `context.companion_changed` recently confirmed you (or another recognized person) are present, narrating it live in the moment ("hey — the dog's sniffing at the cage again") is architecturally simple — an escalation triggered by the co-occurrence of `pet.activity_detected(dog)` and a recent `voice.speaker_recognized` — but needs its own cooldown-heavy reflex rule so it doesn't cry wolf on every minor pass. Not yet built.

### Scenario 3.6 — Distinguishing a calm, distant dog from an alert-worthy close one **[LIVE — this is what proximity thresholds are for]**
`danger_escalation.proximity_danger_cm_max` is specifically the line between "the dog exists somewhere in the room, unremarkable" and "the dog is close enough to warrant a physical response." A dog lying calmly across the room produces no proximity signal at all; only genuine closeness crosses the threshold.

### Scenario 3.7 — The dog's own name being learned and used **[LIVE — same entity_resolver mechanism as the bird]**
Nothing in `entity_resolver.py` is bird-specific; the acquisition/naming patterns match `"dog"` symmetrically to `"bird"`. Everything in [Section 9](#9-naming-entities-and-asking-clarifying-questions) applies equally to the dog.

---

← [Back to top](#pebble--full-capability-catalog)

## 4. Recognizing and treating people differently

### Scenario 4.1 — You speak, and Pebble knows it's you **[STUB — speaker_id.py has the flow, needs a real voiceprint model]**
`voice/speaker_id.py` matches captured audio against enrolled voiceprints stored under `people/voiceprints/`. A match above `voice.speaker_id.match_confidence_min` fires `voice.speaker_recognized` with `person_key: "nigam"`. This routes `prompt_builder.py` to load `prompts/people/nigam.md` — the most private, familiar, unguarded tone Pebble has, explicitly allowed to be teasing or blunt in a way it wouldn't be with anyone else.

### Scenario 4.2 — A family member Pebble hasn't individually profiled yet **[LIVE fallback mechanism]**
If a voice is recognized as belonging to *someone* enrolled but that person doesn't have individualized prompt content, `people/profiles.yaml`'s `family_default` entry provides a warm-but-not-fully-familiar fallback tone — friendlier than a stranger, without pretending the depth of relationship it has with its primary owner.

### Scenario 4.3 — A voice Pebble has never heard before **[LIVE]**
No voiceprint match above threshold → `voice.stranger_detected` fires → `prompts/people/stranger.md` loads — cautious and curious in roughly equal measure, shorter responses, no household details shared. This is deliberately not hostile; it's the same wary-but-interested register a real animal gives an unfamiliar visitor.

### Scenario 4.4 — The same unrecognized voice returning repeatedly **[DESIGNED]**
Currently, repeated strangers don't accumulate any state — every unrecognized utterance is treated identically regardless of how many times that voice has been heard before. A natural extension: track unmatched voiceprint clusters (without assigning them a name) so a *frequently heard but unenrolled* voice could prompt an in-character nudge toward enrollment ("you keep showing up and I still don't know your voice") — this was future idea territory in earlier design passes, not yet implemented.

### Scenario 4.5 — Voice enrollment itself **[STUB — the method exists, needs a real embedding pipeline]**
`speaker_id.py`'s `enroll()` method takes a person key and a list of audio samples (minimum count set by `voice.speaker_id.enroll_min_samples`), and is meant to compute and persist a real voice embedding to `people/voiceprints/{person_key}.npy`. Currently a hook, not live — see the [placeholder audit](#placeholder-and-stub-audit) and the [speaker diarization section](#speaker-diarization-and-user-separation) for exactly which library to use here.

### Scenario 4.6 — Someone asks Pebble to keep a secret from someone else **[DESIGNED, ethically bounded]**
Not currently modeled at all. If built, this would need very deliberate scoping — Pebble's memory and prompt system have no current concept of per-person information barriers (a fact learned from one person is available to the whole household's context by default). This is flagged here explicitly as a gap rather than a roadmap item, since building real information compartmentalization has real privacy design implications worth thinking through carefully before implementing, not treating as a quick feature add.

### Scenario 4.7 — Praise from a specific person landing differently than routine praise **[LIVE mechanism, DESIGNED specific behavior]**
`mood_engine.py`'s `event_deltas` already has a generic `praise` delta. A more specific "showing off in front of company" reaction — where praise while `context.companion_changed` shows a *different* person than the praiser is fresh — would need a small addition checking co-occurrence of a `feedback.praise` event with a recent, distinct `voice.speaker_recognized` for someone else. Not yet built, described fully in future idea #19 from earlier design passes.

---

## 5. Environment awareness — knowing where it is

### Scenario 5.1 — Confirming it's in the bird cage **[LIVE / STUB real sensor thresholds]**
`environment_locator.py` fuses average ultrasonic distance (tight/enclosed reads as cage-like) with recent bird-signature motion, debounced over `environment.location_confirm_window_s` so a single noisy reading can't flip the state. Once confirmed, `environment.location_changed` fires with `location: "bird_cage"`, and `config.yaml`'s `environment.priorities.bird_cage` list (`watch_bird`, `guard_wires`, `monitor_dog_proximity`) becomes the active priority set.

### Scenario 5.2 — Being moved to a desk **[LIVE / STUB real sensor thresholds]**
Open, non-enclosed distance readings without recent bird-signature activity shift the guess toward `"desk"`, activating a different priority set (`watch_person`, `monitor_dog_proximity`) — genuinely different behavior priorities depending on physical context, not just a cosmetic label change.

### Scenario 5.3 — Being somewhere unrecognized entirely **[LIVE]**
If confidence never crosses `environment.location_confidence_min`, location stays `"unknown"`. If this persists past `environment.unknown_location_help_after_s`, the priority set becomes `orient` and `call_for_help_if_prolonged` — genuine uncertainty about its own physical situation is itself treated as worth escalating, not silently tolerated.

### Scenario 5.4 — A promise about location auto-fulfilling itself **[LIVE]**
This is the concrete payoff of environment awareness combined with the commitment system: if you say "I'll put you with the bird in a bit" and later actually place Pebble in the cage, `commitment_watchdog.py`'s subscription to `environment.location_changed` auto-marks the `cage_placement`-kind commitment fulfilled the moment it's physically true — no need to tell it "I did it," because it can verify the claim itself.

### Scenario 5.5 — A physical cage-door sensor replacing the heuristic entirely **[DESIGNED]**
The current distance/motion fusion is explicitly a stand-in for a much more reliable signal — a simple magnetic reed switch on the cage door, or eventually camera-based scene classification, would replace the whole heuristic with something far more trustworthy. The `environment_locator.py` docstring calls this out directly as the intended upgrade path.

### Scenario 5.6 — Zone-level awareness within the cage **[DESIGNED — future idea #1]**
Beyond binary "in the cage or not," a richer spatial model (a cheap way to distinguish "near the water dish" from "near the swing") would let incident memory carry zone tags, enabling much more specific pattern references ("you always do this near the swing") instead of vague generalizations. Not implemented; described fully in the future ideas list below.

---

## 6. Memory — what it keeps, what it forgets, and why

### Scenario 6.1 — A routine sensor blip that means nothing **[LIVE]**
An ambient `sensor.orientation` reading with low urgency and no accompanying mood shift scores poorly on `relevance_scorer.py`'s novelty + emotional-intensity + subject-significance formula, falls below `brain.inspector.relevance_min_score`, and is never stored at all. This is the literal mechanism behind "not everything is worth remembering" — the majority of raw sensor traffic never becomes a memory in the first place.

### Scenario 6.2 — Something mildly interesting but not urgent **[LIVE]**
An event that clears the relevance threshold but doesn't hit any special tier gets `memory_worth_inspector.py`'s default verdict: `ephemeral`, retained for `memory.episodic.retention_days_default` (30 days by default) and then purged by `episodic.py`'s `purge_expired()`.

### Scenario 6.3 — A sudden, sharp positive mood swing **[LIVE]**
If an event's associated mood valence delta crosses `memory_worth.funny_moment_valence_spike_min`, the verdict becomes `notable` regardless of how mundane the raw event looked — this is what lets a genuinely delightful, hard-to-predict moment ("the bird did something ridiculous") get remembered fondly even though nothing about the raw sensor data screamed "important."

### Scenario 6.4 — A fall, a confirmed danger event, critical battery, a prolonged outage **[LIVE]**
Any of these topics is hardcoded in `memory_worth.trauma_keywords_topics` — always `permanent` tier, retained for `memory_worth.trauma_retention_days` (default: 10 years, effectively forever), regardless of how the relevance scorer or mood delta would otherwise have judged it. Safety-critical incidents are never subject to normal forgetting.

### Scenario 6.5 — Getting a new pet **[LIVE]**
`memory.entity_acquired` and `memory.entity_named` are both hardcoded permanent-tier in `memory_worth_inspector.py`, and separately hardcoded to always pass `memory_manager.py`'s storage-candidate filter regardless of what the general blocklist says. The foundational facts of the household — a new pet arriving, being named — are treated with the same permanence as a safety incident, deliberately.

### Scenario 6.6 — The same kind of event happening for the third time **[LIVE]**
`memory_manager.py`'s consolidation pass groups episodic events by `{animal}:{topic}` key. Once a group reaches `memory.consolidation.min_repeats_for_pattern` (default 3) occurrences, it's promoted from "a few isolated incidents" into an actual semantic belief with a confidence score that grows further with each additional occurrence.

### Scenario 6.7 — A belief that contradicts an existing one **[LIVE]**
`contradiction_check.py` compares a candidate fact against existing beliefs about the same subject+object pair. A direct negation (predicate `X` vs. `not_X`) either blocks the write entirely (config: `brain.inspector.contradiction_block: true`) or stores both as unsettled, depending on configuration — real creatures can hold mildly inconsistent working theories, but flat contradictions are still surfaced rather than silently overwritten.

### Scenario 6.8 — Asking "how's the bird been lately" and getting a real answer **[DESIGNED — mechanism exists, standing feature doesn't]**
The pieces exist (episodic storage, tagging by animal, local LLM summarization capability) but nothing currently triggers a summarization pass on-demand as a conversational feature. This is genuinely close to buildable with what's already in place — see future idea list.

### Scenario 6.9 — Memories aging out gracefully rather than growing forever **[LIVE]**
`episodic.py`'s `purge_expired()` runs the retention-tier logic directly in SQL — a single query deletes everything past its tier's cutoff in one pass. This keeps the database bounded over months/years of continuous operation without needing a separate archival process.

### Scenario 6.10 — Recognizing when NOT to remember something **[LIVE, honestly, via omission not suppression]**
There's no explicit "forget this" instruction pathway triggered automatically by content sensitivity — but the relevance/worth pipeline's *default* behavior is conservative: most raw sensor noise simply never crosses the storage threshold in the first place. The system is built to under-remember low-signal events rather than over-remember everything and sort it out later.

---

## 7. Growth over time — opinions that evolve

### Scenario 7.1 — A day-one interaction feeling different from a month-fifty interaction **[LIVE mechanism]**
Every semantic belief in `db_semantic.py` carries a `support_count` and a `confidence` that only grows with repeated corroborating evidence. Early in Pebble's life with a household, `facts_about("bird")` returns sparse, low-confidence entries. Months in, the same query returns a denser, higher-confidence picture — and `prompt_builder.py`'s `memory_context` naturally reflects however much (or little) is actually known at any given point, rather than pretending a fixed level of familiarity from day one.

### Scenario 7.2 — A pattern needing more than a single incident to become an opinion **[LIVE]**
This is the direct purpose of `memory.consolidation.min_repeats_for_pattern` — a single weird incident stays exactly that, an isolated episodic memory, until it recurs enough times to earn promotion into a standing belief. Opinions are earned through repetition, not asserted from one data point.

### Scenario 7.3 — An old belief being revised as more evidence comes in **[LIVE]**
`db_semantic.py`'s `upsert_fact()` doesn't just add new rows for repeated observations — it updates the existing fact's confidence and `support_count` in place, and refreshes `last_updated`. A belief that was weakly held becomes more strongly held (or, via `contradiction_check.py`, gets flagged as unsettled) as new corroborating or conflicting evidence arrives.

### Scenario 7.4 — Referencing "the first time" something happened, specifically **[LIVE mechanism via db_entities.py's acquired_at]**
Because `db_entities.py` preserves the original acquisition timestamp independent of when a name was later learned, and `time_awareness.py` can compute anniversaries via `is_anniversary_of()`, a genuinely "it's been about a year since I got you" callback is architecturally supported — described further in future idea #20 below (seasonal/anniversary callbacks), not yet wired as a standing scheduled feature.

### Scenario 7.5 — A slow-forming caution about the dog vs. a faster-forming fondness for the bird **[DESIGNED — see scenario 3.4]**
Structurally supported (per-subject consolidation thresholds are a config change, not an architecture change) but not yet implemented as an actual asymmetric default.


---

## 8. Commitments — holding you to your word

### Scenario 8.1 — "I'll put you with the bird in a bit" **[LIVE]**
A voice-detected promise (parsed by whatever intent-recognition sits in front of `db_commitments.py` — currently the LLM path, since natural promise phrasing genuinely needs language understanding) creates a `pending` commitment with `kind: "cage_placement"`, a `made_at` timestamp, and either an explicit or a default vague-promise wait time (config: `commitment_watchdog.vague_promise_default_wait_s`, default 30 minutes for phrasing like "in a bit").

### Scenario 8.2 — You actually follow through **[LIVE]**
As covered in scenario 5.4 — `environment.location_changed` firing with `location: "bird_cage"` auto-fulfills any pending `cage_placement` commitment. No further input needed from you; Pebble verifies the claim itself via its own environment model.

### Scenario 8.3 — You don't follow through, and enough time passes **[LIVE]**
`commitment_watchdog.py` polls every `commitment_watchdog.check_interval_s` (default 60s). Once `now >= expected_by + grace_period_s`, the commitment is overdue. `commitment.overdue` fires with `minutes_overdue` and a humanized time-ago string, at `commitment_watchdog.overdue_urgency` (deliberately ambient-tier, 0.35, not alarm-tier — this is a nag, not an emergency).

### Scenario 8.4 — The nag actually being spoken, not just logged **[LIVE, once wired per the personality.py fix discussed during development]**
`commitment.overdue` needs to be included in `personality.py`'s `_needs_deliberation()` allowlist for the LLM to actually generate spoken language about it — the reflex table alone only produces the visual `expression.pointed_reminder`, not words. With both wired, the LLM receives the real elapsed time and phrases something naturally mood-colored — sharper if the current mood is annoyed/bored, more like genuine puzzlement if curious.

### Scenario 8.5 — Not repeating the same nag every minute **[LIVE]**
`commitment_watchdog.renag_interval_s` (default 15 minutes) prevents re-firing the same overdue notice on every single poll cycle — it surfaces, then waits a reasonable interval before surfacing again if still unresolved.

### Scenario 8.6 — A commitment about something other than location **[LIVE — schema supports any kind]**
`db_commitments.py`'s schema has a generic `kind` and `subject` field, not just `cage_placement`. A promise about feeding, a walk, anything spoken with promise-shaped language can be tracked the same way; only the *auto-fulfillment* logic is currently location-specific (subscribing to `environment.location_changed`). Other kinds would currently need to be manually resolved (or a corresponding auto-detection signal added) rather than self-verifying.

### Scenario 8.7 — Saying sorry after being called out **[DESIGNED]**
Currently a broken commitment just sits, nagged periodically, with no path to being marked `forgiven` rather than perpetually `pending`/`broken`. Real relational repair — recognizing an apology shortly after a nag and softening the associated mood delta, marking the commitment resolved with a different status — is described in the future ideas list, not yet implemented.

### Scenario 8.8 — Someone's reliability affecting how commitments from them are treated in the future **[DESIGNED]**
A trust/reliability signal per person (separate from affection) — someone who reliably follows through vs. someone who doesn't — could shift how skeptically a *future* promise from them is treated ("you said that last time too"). This is a `db_people.py` field addition, not a new subsystem, described in the future ideas list.

---

## 9. Naming, entities, and asking clarifying questions

### Scenario 9.1 — "I got a bird" **[LIVE]**
`entity_resolver.py`'s acquisition pattern matches, creates an entity stub via `db_entities.py`'s `create_stub(kind="bird")` with `name: NULL` and `acquired_at` set to right now. `memory.entity_acquired` fires, tagged `is_notable: true`, and — per Section 6 — is hardcoded permanent-tier regardless of how routine the raw statement otherwise looks.

### Scenario 9.2 — "Her name is Ken," said three days later **[LIVE]**
The naming pattern matches. `find_unnamed_stub("bird")` locates the entity created three days prior. `set_name()` fills in `name` and `named_at` — critically, leaving `acquired_at` completely untouched. `memory.entity_named` fires with both timestamps in the payload, so anything downstream (memory context for an LLM call, a future summary) can correctly say "I've known you three days longer than I've known your name" rather than treating naming as if it reset the whole relationship's clock.

### Scenario 9.3 — Referring to "Ken" afterward, with zero ambiguity **[LIVE]**
Once named, `find_by_name("Ken")` succeeds on any future mention — no special handling needed, it's now a fully resolved entity like any other.

### Scenario 9.4 — Hearing a name with no prior context at all **[LIVE]**
If "Ken" is mentioned ("I went with Ken today") with no unnamed stub to attach to and no existing entity match, `_try_handle_ambiguous_reference()` catches it via the unresolved-reference pattern, filters out common false-positive capitalized words (days of the week, "I", "The", etc.), and raises a real open question in `db_open_questions.py` rather than silently guessing or silently ignoring it.

### Scenario 9.5 — The question actually being asked out loud **[LIVE — reflex + escalation both wired]**
`brain.clarification_needed` fires the `ask_clarifying_question` reflex (instant `expression.curious_question` — a head-tilt, essentially) AND is in `_needs_deliberation()`'s allowlist, so the LLM generates the actual spoken question, guided by `prompts/response_rules_clarification.md`'s instruction to sound genuinely curious ("wait, who's Ken?") rather than database-flavored ("I don't have that information on file").

### Scenario 9.6 — You answer the question **[LIVE]**
`_try_resolve_pending_question()` runs *first*, before any other transcript handling, checking `db_open_questions.py`'s `most_recent_open()`. A confirmation pattern match (currently: mentioning "bird"/"dog" alongside an affirmative word) resolves the pending question, names the correct stub, and marks the question resolved with a record of exactly what it resolved to.

### Scenario 9.7 — You never answer, and time passes **[LIVE]**
`db_open_questions.py`'s `abandon_stale()` marks any open question older than `memory.open_questions.stale_after_s` (default 3 days) as `abandoned` rather than leaving it open forever, waiting for an answer that may never come.

### Scenario 9.8 — Multiple unnamed pets at once **[LIVE, conservatively]**
If more than one unnamed stub exists across kinds when a name arrives, `_try_handle_naming()` deliberately does NOT guess — it routes to the same ambiguous-reference path rather than risk misattributing a name. Safer to ask than to guess wrong on something this foundational.

### Scenario 9.9 — Renaming an already-named pet **[DESIGNED]**
"Actually, call him Max instead" isn't currently distinguished from an entirely fresh, ambiguous naming attempt. Detecting the "actually/instead" framing and updating the existing entity's name (moving the old name to a `notes` field as history rather than blocking it as a contradiction) is described in the future ideas list.

### Scenario 9.10 — A second pet of the same kind **[DESIGNED — flagged gap, see scenario 2.8]**
Requires explicit "another/second/new" language detection to avoid misattributing a name meant for a second bird onto the first bird's still-unnamed stub.

### Scenario 9.11 — Correcting a wrong entity guess **[DESIGNED, see scenario 2.9]**
No current mechanism for "no, Ken's the dog" to correct a prior misattribution rather than being treated as a brand new statement.

### Scenario 9.12 — Pronoun resolution across a conversation **[DESIGNED]**
"Ken did something funny earlier... he's always like that" — the second sentence's "he" isn't currently resolved to Ken at all; `entity_resolver.py` only pattern-matches capitalized name-shaped words, not pronouns. A short-lived "most recently discussed entity" pointer, checked before falling through to the ambiguous-reference path, would close this — described in the future ideas list.

### Scenario 9.13 — A soft guess instead of always demanding a full stop-and-ask **[DESIGNED]**
Not every ambiguity needs the full clarification flow. If exactly one entity of a plausible kind exists (named or not), a medium-confidence soft guess spoken aloud ("you mean Ken, right?") with an implicit-confirmation-by-silence pattern would feel more fluid than always raising a formal open question. Described in the future ideas list; not yet implemented.

---

## 10. Mood and personality expression

### Scenario 10.1 — Resting state is curiosity, not neutrality **[LIVE]**
`mood_engine.py`'s `_discretize()` deliberately defaults to `"curious"` rather than a flat neutral label when no other threshold is crossed — a specific character choice, not an implementation accident, matching the "curious first" personality quirk.

### Scenario 10.2 — Boredom building up over a quiet stretch **[LIVE]**
With no events nudging mood and enough time passing, valence/arousal decay toward baseline (config: `mood.decay_half_life_s`). If baseline arousal is itself low and nothing's happened in a while, the discretized state settles into `"bored"` — and `prompts/mood/bored.md`'s guidance ("nothing's held your attention... you might unprompted mention wanting something to happen") shapes any generated speech accordingly.

### Scenario 10.3 — A startle spiking arousal sharply **[LIVE]**
`mood.event_deltas.startle` is a large negative valence, large positive arousal delta — a single fall or possible-fall event can swing the discretized mood dramatically in one step, distinct from the gradual drift of ordinary events.

### Scenario 10.4 — Excitement at a specific person's arrival **[LIVE mechanism]**
`mood.event_deltas.person_recognized` gives a positive valence/arousal nudge on any recognized speaker — combined with high arousal crossing `mood.states.excited_arousal_min`, this can tip mood into `"excited"`, loading `prompts/mood/excited.md`'s guidance toward quicker, more breathless, more mischief-prone language.

### Scenario 10.5 — Annoyance burning off quickly rather than lingering **[LIVE mechanism, DESIGNED per-annoyance-source persistence]**
`mood.decay_half_life_s` governs overall mood decay generically. A *specific* grudge toward a specific subject (annoyed at the dog specifically, independent of general mood) with its own decay curve isn't currently modeled — mood is a single global point, not per-subject. Described as future idea #6 (a temporary negative modifier attached to a specific subject) in the ideas list below.

### Scenario 10.6 — Mood driving which face sprite plays **[STUB — sprite assets don't exist yet, wiring does]**
`face/animator.py` looks up `idle_{current_mood}` sprite sequences and blends them with brief reflex-triggered overlays. The blending logic is real; the actual sprite image assets referenced by `body/face/sprites/` are placeholder paths with no art yet (see [placeholder audit](#placeholder-and-stub-audit)).

### Scenario 10.7 — Mood driving RGB color, readable across a room **[LIVE wiring / STUB real LED hardware write]**
`rgb_visualizer.py` maps the current mood label straight to a configured hex color (`body.rgb.colors`) and applies it — deliberately louder/more glanceable than the face, meant to be readable at a glance from across the room, not up close.

### Scenario 10.8 — Mischief showing up specifically in high-energy moods **[LIVE, as prompt guidance]**
`prompts/mood/excited.md` explicitly calls out that the mischievous personality trait is "most likely to surface" during excitement — high energy plus low inhibition pairing naturally, written directly into the mood's tone guidance rather than left to chance.

### Scenario 10.9 — Personality staying consistent across completely different situations **[LIVE, by construction]**
Because `prompt_builder.py` *always* includes `core_identity.md` and `personality_quirks.md` regardless of trigger, the underlying character — curious-first, mildly mischievous, protective of the bird, no false cheerfulness — is a structural constant layered under every mood/mode/person variation, not something that has to be separately maintained per scenario.

### Scenario 10.10 — Editing personality without touching code **[LIVE, by design]**
Every one of the above is driven by plain markdown files under `prompts/`. Wanting a calmer Pebble, a more food-motivated one, a different relationship to the dog specifically — all of it is a text edit, never a Python change. This is one of the most deliberate architectural choices in the whole project.

---

## 11. Privacy and operating modes

### Scenario 11.1 — Flipping the physical privacy switch **[LIVE / STUB real GPIO read]**
`sensors/dpdt_mode_switch.py` reads the switch position, publishes `sensor.mode_switch_changed`. `operating_mode.py` immediately transitions to `privacy` mode — cloud LLM calls disabled, audio persistence disabled, the face/RGB show a fixed, unmissable privacy-indicator color (config: `operating_mode.privacy.face_indicator_color`).

### Scenario 11.2 — Software cannot override the physical switch **[LIVE, tested]**
`operating_mode.py`'s `_reconcile_and_apply()` explicitly checks: if the physical switch is asserting privacy and a software command tries to set anything other than privacy, the request is silently ignored. `tests/test_operating_mode.py` verifies this exact invariant. This exists specifically so a network bug, a misbehaving remote-bridge command, or a compromised software layer can never silently disable a privacy guarantee you set by hand.

### Scenario 11.3 — Software freely switching modes when privacy isn't physically engaged **[LIVE, tested]**
When the physical switch is in its normal position, `network.mode_command` events (e.g., from `remote_bridge.py`) can freely move between `normal` and `debug` — the override protection is specifically scoped to privacy, not a blanket lock on all mode changes.

### Scenario 11.4 — Behavior actually changing under privacy mode, not just a badge **[LIVE mechanism]**
`llm_router.py` explicitly checks `operating_mode.is_privacy()` before ever considering a cloud call — even if local confidence is low, privacy mode forces a local-only fallback response rather than escalating. `prompts/modes/privacy.md` additionally instructs any generated speech to stay brief and surface-level, not forming or referencing detailed memories of what's said during that window.

### Scenario 11.5 — Debug mode revealing internal state without breaking character **[LIVE, as prompt guidance]**
`prompts/modes/debug.md` draws a careful line: Pebble can answer direct, sincere questions about its own mood/recent events factually — but never describes its own architecture, modules, or config. "I got annoyed because the dog kept getting close" is in character; naming an event bus or a config key is not, even in debug mode.

### Scenario 11.6 — A stranger triggering more guarded behavior automatically **[LIVE]**
This isn't a separate "mode" — it's `prompts/people/stranger.md` loading whenever `voice.stranger_detected` fires, layered on top of whatever the current mood/operating mode already is. Guardedness toward an unrecognized voice and privacy mode are two independent, stackable axes.

### Scenario 11.7 — Debug mode's verbose event logging being genuinely toggleable **[LIVE]**
`main.py`'s boot sequence checks `operating_mode.debug.verbose_event_log` from config before subscribing a firehose debug logger to the bus — flip one config value, no code change, to go from silent operation to seeing every single event logged live.

---

## 12. Power and self-monitoring

### Scenario 12.1 — Battery drains gradually and nothing happens until it matters **[LIVE / STUB real ADC read, LIVE mock drain curve]**
`power_manager.py` polls voltage every `power.poll_interval_s`, converts to percentage using the configured full/empty voltage curve, and publishes ambient `power.battery_level` on every single poll — but only fires `power.low_battery` / `power.critical_battery` on threshold *crossings*, not repeatedly, so normal operation isn't spammed by routine battery telemetry.

### Scenario 12.2 — Dev-mode battery simulation for testing without real hardware **[LIVE]**
`power/mock_power.py` simulates a smooth drain curve from full to empty over a configurable duration, purely so `power_manager.py` has something real to react to during development — the exact same pattern as `mock_sensors.py` for sensing and `mock_display.py` for output.

### Scenario 12.3 — Low battery producing a visibly different reaction than critical battery **[LIVE reflex / needs the two rules added per development discussion]**
`power.low_battery` (urgency 0.7) and `power.critical_battery` (urgency 1.0) are meant to map to distinct reflexes — `expression.tired_and_worried` vs. `expression.panicked_low_power` — a graduated physical response matching the graduated severity, the same pattern used for bird-danger escalation.

### Scenario 12.4 — Critical battery actually being spoken about, grounded in the real number **[LIVE mechanism]**
`power.critical_battery` is included in `personality.py`'s `_needs_deliberation()` allowlist specifically so it can escalate to the LLM — and `prompt_builder.py`'s `battery_percent` parameter means anything generated is grounded in the actual measured percentage from the event payload, never invented or guessed by the model.

### Scenario 12.5 — Power state changing the whole system's behavior, not just battery messaging **[LIVE]**
`power/modes.py` defines throttle and sensor-poll-multiplier settings per power state (`normal`/`low_power`/`critical`) — a real system-wide slowdown under low power, not merely a cosmetic status change. Other modules can query `PowerModes.sensor_poll_interval()` to scale their own polling rate down as battery gets scarce.

### Scenario 12.6 — Battery escalation reaching a human the same way bird-danger does **[DESIGNED — hookup described, not yet wired]**
Extending the same `AmpController`/`VibrationMotor` staged-escalation pattern already built for bird danger to critical battery would give it the same "gets louder if ignored, eventually calls for real help" behavior. Described in the [placeholder audit](#placeholder-and-stub-audit) as a specific, scoped addition.

---

## 13. Network resilience and calling for help

### Scenario 13.1 — A brief connectivity blip **[LIVE]**
`connection_watchdog.py` requires `network.watchdog.offline_after_missed` consecutive failed pings before even declaring itself offline — a single dropped packet doesn't trigger anything, avoiding false alarms from routine network jitter.

### Scenario 13.2 — Genuinely losing connectivity for an extended period **[LIVE]**
Once offline is confirmed, `network.status_changed` fires immediately (urgency 0.5) — a real state change worth knowing about even before it becomes an emergency.

### Scenario 13.3 — An outage persisting long enough to become a real concern **[LIVE]**
Past `network.watchdog.call_for_help_after_s` (default 5 minutes) of continuous confirmed offline state, `network.prolonged_outage` fires at urgency 0.9 — treated with nearly the same seriousness as a physical danger event, on the reasoning that a companion cut off from the outside world for that long is itself a vulnerability worth surfacing.

### Scenario 13.4 — Connectivity returning **[LIVE]**
`_handle_reachable()` resets all outage tracking state and, if it was previously offline, fires `network.status_changed` with `online: true` — the recovery is itself a notable transition, not just a silent return to normal.

### Scenario 13.5 — `system.call_for_help` actually reaching someone **[DESIGNED — messenger.py exists, needs live provider implementation]**
This is the single most consequential remaining gap in the whole system. Every escalation path — bird danger, critical battery, prolonged outage — converges on this one event topic. `network/messenger.py` is built to receive it and attempt delivery via ntfy.sh/Telegram/Twilio, but the actual HTTP calls are still `SENSOR INPUT HOOK` stubs. Closing this gap is what turns "calls for help like a startled pet" from a locally louder speaker into something that reaches you when you're not in the room. See the [placeholder audit](#placeholder-and-stub-audit) for exactly which functions need real implementations.

### Scenario 13.6 — Not spamming every configured contact simultaneously **[LIVE]**
`messenger.py`'s `_on_call_for_help()` iterates through `priority_targets` in order and stops at the *first* successful delivery — a graceful fallback chain (try Nigam, then family_default) rather than blasting every household member's phone at once for a single incident.

### Scenario 13.7 — Rate-limiting so a stuck sensor can't spam a phone **[LIVE]**
`messenger.py`'s `_passes_rate_limit()` enforces `messaging.rate_limit_min_interval_s` per recipient — even a hardware fault causing repeated `system.call_for_help` events can't flood someone's phone with the same alert every few seconds.

### Scenario 13.8 — A remote dashboard toggling privacy mode **[LIVE mechanism / STUB real server]**
`remote_bridge.py`'s `_handle_command()` validates a bearer token (config: `REMOTE_BRIDGE_TOKEN` in `.env`) before translating an incoming command into a `network.mode_command` bus event — the actual HTTP/WebSocket server binding is a hook, but the auth and translation logic is real.


---

## 14. Voice, speech, and conversation

### Scenario 14.1 — Not running expensive speech recognition on every ambient sound **[LIVE / STUB real VAD classifier]**
`voice/vad.py` runs continuous, cheap frame-by-frame speech/non-speech classification. Only once actual speech is detected AND `voice.vad.silence_timeout_s` of subsequent quiet confirms the utterance is complete does a buffer get handed to STT — the expensive Whisper model stays idle almost all the time, mirroring the whole system's "cheap local check before expensive processing" philosophy applied specifically to audio.

### Scenario 14.2 — Transcribing what was actually said **[STUB — needs a real Whisper model loaded]**
`stt_whisper.py` wraps a local Whisper-family model sized by `voice.stt.model_size` (default `base.en`, a reasonable accuracy/speed tradeoff for a resource-constrained device). Publishes `voice.transcript_ready` — one of the small set of topics that actually triggers deliberation.

### Scenario 14.3 — Recognizing who's speaking, independent of what they said **[STUB — needs a real voiceprint embedding pipeline]**
`speaker_id.py` runs in parallel with STT on the same captured utterance — identity and content are treated as genuinely independent questions, computed separately. See the full [speaker diarization section](#speaker-diarization-and-user-separation) for the specific library recommendation.

### Scenario 14.4 — Speaking back, in a voice/rate that varies per person **[STUB — needs edge-tts wired live]**
`tts_edge.py` wraps `edge-tts` (free, neural-quality, no API key required) and resolves a per-person voice override from `people/profiles.yaml`'s `tts_voice` field before synthesizing — Nigam might hear a different voice/rate than a stranger interaction would produce.

### Scenario 14.5 — A spoken response that's too long **[LIVE]**
`response_inspector.py` enforces a maximum spoken word count (`_MAX_SPOKEN_WORDS`, currently 40) on every generated response before it ever reaches TTS — truncating with a trailing ellipsis if exceeded. A real creature doesn't monologue, and this is enforced mechanically, not just requested via prompt instruction.

### Scenario 14.6 — A response that sounds like an AI assistant rather than a creature **[LIVE]**
`response_inspector.py`'s `_ASSISTANT_TELLS` regex list catches phrases like "as an AI" or "I am a language model" and rejects the response outright rather than let it reach voice/body — a hard mechanical backstop underneath the prompt-level instruction to never break character.

### Scenario 14.7 — Never fabricating a memory that wasn't actually retrieved **[LIVE, as an enforced prompt rule]**
`response_rules.md` explicitly instructs: if situational memory context is empty or doesn't cover the topic, the correct in-character response is "first I'm hearing of it," never an invented anecdote. This is a rule enforced by instruction rather than a hard mechanical filter (unlike the assistant-tell check), so it depends on the underlying model actually following it — worth noting as a real, if soft, limitation.

### Scenario 14.8 — An instant warning that bypasses the LLM entirely **[LIVE]**
`tts_edge.py`'s subscription to `danger.escalation_stage` uses a fixed phrase bank keyed by escalation pattern, not a generated response — deliberately, because a real animal's alarm call is reflexive and immediate, not composed on the fly. This is the one voice output path with zero LLM latency.

### Scenario 14.9 — Volume actually changing based on how urgent the moment is **[STUB — wiring exists, needs real amplifier/gain control]**
`amp_controller.py` translates `danger.escalation_stage`'s `volume_multiplier` into an actual playback gain change, resetting to baseline on `danger.cleared`. The volume physically audible during a real emergency should be meaningfully louder than routine conversational volume.

### Scenario 14.10 — A genuinely two-way conversation, not a single question-answer exchange **[DESIGNED, partially supported]**
The `db_open_questions.py` mechanism supports one specific kind of multi-turn continuity (resolving a pending clarification). A more general conversational memory across several consecutive exchanges — tracking topic continuity beyond just open questions — isn't currently modeled as its own subsystem.

---

## 15. Music and audio

### Scenario 15.1 — "Play some music" resolving to an actual song **[STUB — needs a live yt-dlp subprocess call]**
`music_player.py` uses `yt-dlp`'s built-in search syntax (`ytsearch1:<query>`) to resolve a plain-text request to a single best-match result — no separate search API, no API key, entirely free. The result is downloaded to a local cache directory, played, and the cache entry expires after `music.cache_max_age_s`.

### Scenario 15.2 — Not accumulating a permanent music library **[LIVE, by design]**
`purge_stale_cache()` removes any cached audio file older than the configured max age — this is deliberately an on-demand streaming behavior, not a library manager. Nothing in the design intends for Pebble to hoard music.

### Scenario 15.3 — Music volume respecting the same danger-escalation override as speech **[DESIGNED — noted as an integration point, not yet wired]**
`music_player.py`'s actual playback hook should route through the same `amp_controller.py` volume path TTS uses, so if a danger event fires mid-song, the alert can still cut through at proper volume rather than being drowned out by music playing at a separate, uncoordinated volume level.

### Scenario 15.4 — A failed music request being handled gracefully **[LIVE mechanism]**
`play()` wraps the resolve/download step in a try/except and publishes `music.playback_failed` with the actual error on failure — a failed search or network hiccup produces a clear signal rather than a silent no-op.

### Scenario 15.5 — Voice-triggered music requests **[DESIGNED — needs an intent layer]**
Currently `music.play_requested` is the entry event, but nothing yet parses "play [song]" out of a raw transcript into that specific event with the song name extracted — this intent-recognition step would live either as a fast local pattern match (similar to `entity_resolver.py`'s regex-based approach) or as an LLM-classified intent, not yet built either way.

---

## 16. Messaging real humans

### Scenario 16.1 — ntfy.sh as the simplest possible path **[STUB — needs one live HTTP POST]**
No account, no API key, free, no per-message cost. A person subscribes to a private topic string in the ntfy app; anyone (or anything) that knows that topic string can push to it via a plain unauthenticated HTTP POST. The entire security model is "the topic name is the shared secret" — worth picking a genuinely hard-to-guess topic string, not something like `pebble-alerts`.

### Scenario 16.2 — Telegram as a free, official alternative **[STUB — needs a bot token + one live HTTP call]**
Free, official Bot API, no per-message cost, no risk to any personal phone number. Setup is a short conversation with Telegram's `@BotFather` to get a token, then each recipient needs their own `chat_id` (obtained by messaging the bot once and reading the response). More setup than ntfy, more robust/official than ntfy's open-topic model.

### Scenario 16.3 — Twilio SMS reaching a phone number directly, no app required **[STUB — needs the Twilio SDK wired + real credentials]**
The only option here that doesn't require the recipient to install anything — lands as a plain text message. Costs roughly $0.008 per message in most regions, pay-as-you-go, no monthly fee. The realistic choice specifically for someone who might not install ntfy or Telegram.

### Scenario 16.4 — Why WhatsApp specifically isn't a free, reliable option **[Documented limitation, not a bug]**
Meta's official WhatsApp Business API charges per conversation outside a 24-hour window that must be opened by the *other person* messaging first — there's no free way to originate an arbitrary outbound WhatsApp message to someone who hasn't messaged first. Unofficial browser-automation approaches exist but violate WhatsApp's Terms of Service and risk the sending phone number being banned; deliberately not built here.

### Scenario 16.5 — A single message reaching the first available recipient, not everyone at once **[LIVE, see scenario 13.6]**

### Scenario 16.6 — Adding a new contact for messaging without touching code **[LIVE]**
`people/profiles.yaml` and `messaging`'s per-provider target maps in `config.yaml` are the only things that need editing to add a new reachable person — no Python changes required.

### Scenario 16.7 — A live Google Contacts sync instead of typed-in names **[DESIGNED, explicitly discouraged unless there's a specific need]**
Technically buildable via OAuth2 + the Google People API, but represents a meaningfully larger security surface (a token capable of reading an entire contact list, held on a device sitting in a bird cage on a home network) for a benefit — having a name instead of a raw identifier — that a one-time manual config entry achieves at essentially zero risk. Documented here as a considered-and-deprioritized option, not a roadmap item.

---

## 17. Physical expression — face, light, sound, touch

### Scenario 17.1 — The face reacting instantly to a reflex, then returning to idle **[LIVE wiring / STUB real sprite assets and OLED driver]**
`face/animator.py`'s render loop checks for an active reflex-triggered overlay expression first; if one's active and still within its brief window (`~1.5s`), it plays that sprite sequence, interrupting whatever idle mood animation was running. Once the overlay window ends, it falls back to `idle_{current_mood}`.

### Scenario 17.2 — Natural, involuntary-feeling blinking **[LIVE wiring / STUB real sprites]**
The render loop schedules the next blink at a randomized interval (config: `body.face.animator.blink_interval_s_range`) rather than a fixed cadence — avoiding the uncanny, mechanical feel of a perfectly regular blink pattern.

### Scenario 17.3 — Privacy mode overriding all expression with one unmissable signal **[LIVE wiring / STUB real display]**
When `operating_mode.is_privacy()` is true, `face/animator.py`'s render loop skips both idle and reflex expressions entirely and draws a fixed privacy indicator instead — nobody in the house should ever have to wonder whether Pebble might be paying attention right now.

### Scenario 17.4 — Mood readable from across a room, not just up close **[LIVE wiring / STUB real LED write]**
`rgb_visualizer.py` exists specifically because the OLED face requires proximity to read, but a colored light doesn't — the two displays serve genuinely different purposes (detail vs. glanceability) rather than duplicating the same information in two places.

### Scenario 17.5 — A terse numeric readout for debugging, without cluttering the expressive face **[LIVE wiring / STUB real seven-segment write]**
`seven_segment.py` only actively displays anything when `operating_mode.debug.show_internal_state_on_face` is true — battery percentage, mostly — kept deliberately separate from the emotionally expressive face so debug info never contaminates the "alive creature" illusion during normal operation.

### Scenario 17.6 — A physical "back off" that doesn't require sound **[STUB — needs a real PWM motor driver]**
`vibration_motor.py` fires a distinct buzz pattern for close-range proximity warnings even before a full danger event is confirmed (`sensor.close_proximity_warning`), and intensifies alongside the same escalation stages the speaker volume responds to for confirmed danger — a touch-based signal, useful even in a loud room where sound alone might not register.

### Scenario 17.7 — Distinct vibration patterns for distinct situations **[LIVE as configuration, STUB as real hardware output]**
`body.vibration.patterns` in config defines pulse count, intensity, and timing per situation (`close_warning`, `chirp_alert`, `loud_distress`, `sos_loop`) — a small vocabulary of distinguishable physical signals rather than one generic buzz for everything.

### Scenario 17.8 — Audio output eventually reaching a proper Bluetooth speaker rather than a tiny onboard one **[DESIGNED — see full explanation below]**
See the [Bluetooth and external audio](#bluetooth-and-external-audio) section for the complete explanation of the ESP32-as-bridge design and why it's structured that way.


---

## 18. The 35 future ideas

Every idea below is scoped to say *where* it would live in the existing codebase, not just what it would do — the goal is that any of these should be startable without first re-deriving the architecture.

### 1. Zone-level spatial memory within the cage
Rather than one blob of "in the cage or not," track a rough internal zone map — "near the water dish," "near the swing side" — using relative signal strength/timing differences from the existing ultrasonic sensor, no new hardware required. Incident memory tagged with a zone lets Pebble say "you always do this near the swing" instead of a vague generalization. Lives in `environment_locator.py` as an extension, with a new `zone` field added to episodic memory's tags.

### 2. Bird mood mirroring, inverted
If the bird's activity/sound level has been elevated for a sustained stretch, Pebble's own arousal should route partly into a distinct "guardian" sub-state rather than generic excitement — protective watchfulness reads differently than being personally thrilled about something. Would need a new mood dimension or a tagged sub-state inside `mood_engine.py`, not just a bigger generic arousal delta.

### 3. A "tattling" instinct with real cooldown
Already scoped as scenario 3.5 above — narrating dog-near-cage behavior live when a recognized person is nearby, heavily rate-limited so it doesn't cry wolf. The main design risk is exactly that rate limiting; without it, this becomes annoying almost immediately.

### 4. Distinct alarm calls per danger type
Currently the escalation *stages* (chirp → loud → SOS) are distinguishable from each other, but a fall, a stranger at the door, and bird-danger all currently funnel toward similar-sounding urgency. A small, genuinely distinguishable vocabulary of 3-4 alarm sound/light patterns — distinct enough that someone across the room could tell severity/type apart without looking — would live in `body/rgb_visualizer.py` and `voice/tts_edge.py`'s phrase bank as parallel, type-specific pattern sets.

### 5. A temporary, subject-specific grudge that decays independently
Global mood already decays toward baseline. A *targeted* negative modifier — "annoyed at the dog specifically" — with its own separate decay timer distinct from overall mood would let Pebble be simultaneously sleepy-in-general and still huffy at one specific housemate. Would need a small dict of `{subject: (modifier, decay_start_time)}` inside `mood_engine.py`, queried by `prompt_builder.py` when a pet-specific prompt fragment is being assembled.

### 6. First-of-its-kind excitement
The very first time `memory.pattern_detected` fires for a brand-new subject/predicate combination (not just another supporting occurrence of an existing belief), that specific moment deserves a distinct small excitement spike — noticing something new is different from confirming something already suspected. A one-line check in `personality.py`'s handling of `memory.pattern_detected` distinguishing "first occurrence of this pattern" from "reinforcement of an existing one."

### 7. A physical flinch-away motor reflex
If a servo or wheel base is ever added, true reflex-tier events (a fall, a loud bang) could trigger an actual small physical flinch/backup motion — closing the loop between "startled" as a facial expression and an actual body movement. Would live as a new `body/motor_reflex.py` module subscribing to the same high-urgency events the face already reacts to.

### 8. Voice enrollment as an in-character mini-ritual
Rather than a settings-menu flow, repeated failed voice matches for the same unrecognized voice could prompt Pebble to get "curious enough" to initiate enrollment conversationally ("you keep showing up and I don't know your voice yet") — turning a necessary onboarding step into something that feels like the creature's own initiative rather than admin work. Lives in `speaker_id.py`, tracking unmatched-voice frequency, escalating to a spoken prompt via the LLM path.

### 9. Weather/light-level correlation with mood baseline
A cheap ambient light sensor, correlated over weeks with observed activity level, could let a "grumpy on dark mornings" pattern emerge organically — genuinely creature-like, and achievable with the existing consolidation pipeline plus one new cheap sensor, no ML model required.

### 10. A private "diary" spoken only in privacy mode
Ironically, privacy mode — specifically because nothing said during it gets persisted — could be the moment Pebble is most willing to muse out loud unprompted, since there's no risk of it becoming a stored memory. A small, deliberately unguarded personality surface gated specifically to that mode.

### 11. Escalating "calling for help" with real stages, not one flat alarm
Already partially designed for bird-danger and described for battery — the general pattern (chirp → louder → full alarm → actually message a human) should become the *standard* shape for every self-preservation scenario, not something built separately each time. Worth formalizing `DangerEscalationTracker` into a reusable base class other trackers (battery, network outage) could inherit from, rather than reimplementing the staged logic per scenario.

### 12. Environment-aware volume and brightness auto-scaling
Using ambient light/noise baselines (from PIR/mic activity patterns over time) to auto-scale RGB brightness and TTS volume so Pebble isn't jarringly loud/bright in a quiet room at 2am, without needing an explicitly scheduled "night mode." Ties naturally into `time_awareness.py`'s quiet-hours detection as an additional continuous signal rather than a hard on/off switch.

### 13. A local, cost-free "how's the bird been" logbook narrator
Already scoped as scenario 2.10 and 6.8 above — using the local LLM (no cloud cost) to periodically summarize recent bird-tagged episodic memories into a natural narrative on request. The most immediately buildable idea on this entire list given what already exists.

### 14. Distinguishing a fall from being picked up, by acceleration profile
Already scoped as scenario 1.3 — a real fall is a sharp, brief spike; being lifted is smoother and more sustained. Requires capturing a short window of IMU samples around the trigger threshold rather than reacting to a single instantaneous reading, a meaningful but scoped change to `mpu6050.py`'s sampling logic.

### 15. Territorial "opinion drift" — asymmetric consolidation thresholds
Already scoped as scenario 3.4/7.5 — dog-related beliefs requiring more repeated evidence than bird-related ones before consolidating, reflecting that dog encounters in a shared household are inherently noisier than the bird's fixed routine. A config-level per-subject override on `memory.consolidation.min_repeats_for_pattern`.

### 16. A self-initiated event during prolonged boredom
When bored mood persists past a threshold with zero new events, occasionally initiating something small unprompted — a soft ambient sound, an idle animation variation — rather than only ever reacting to external triggers. This is the difference between a device that waits to be poked and one with genuine idle behavior of its own; would live as a new timer-driven check inside `personality.py` alongside the existing reflex table.

### 17. Contextual quietness around a sleeping/resting bird
Already scoped as scenario 2.4 — if the bird has been still for an unusually long stretch during its normally-active hours (learned from accumulated pattern data, not a fixed schedule), treat that specially: either "probably asleep, stay quiet" as a default, or, if the stillness persists further past what's normal, flag it as genuinely worth a person's attention.

### 18. A "proud" reaction to praise witnessed by someone else
Already scoped as scenario 4.7 — praise while a *different* person than usual is freshly present triggers a slightly higher excitement spike than routine praise, the "showing off in front of company" instinct.

### 19. Seasonal and anniversary callbacks
Already partially supported via `time_awareness.is_anniversary_of()` — a scheduled once-daily check comparing today's date against notable permanent-tier episodic memories' timestamps, surfacing a natural callback ("this is around when you first came home") when a match falls within tolerance. The single most emotionally resonant idea on this list relative to how little new code it needs.

### 20. Renaming with explicit "actually/instead" detection
Already scoped as scenario 9.9 — distinguishing a deliberate rename from a fresh ambiguous naming attempt, preserving the old name as history rather than treating it as a blocked contradiction.

### 21. A "last discussed entity" pointer for pronoun and correction handling
Already scoped as scenarios 9.11 and 9.12 — a short-lived pointer to whichever entity was most recently resolved in conversation, checked before falling through to the ambiguous-reference path, enabling both pronoun resolution ("he's always like that") and correction handling ("no, Ken's the dog").

### 22. Confidence-scored soft guesses instead of always demanding confirmation
Already scoped as scenario 9.13 — a medium-confidence situation (exactly one plausible entity exists) warranting a spoken soft guess with implicit confirmation-by-non-correction, rather than always raising the heavier formal open-question flow.

### 23. Repair and forgiveness for broken commitments
Already scoped as scenario 8.7 — recognizing apology-shaped language shortly after a nag, softening the associated mood delta, and marking the commitment `forgiven` rather than leaving it in permanent unresolved limbo.

### 24. A per-person reliability/trust signal, separate from affection
Already scoped as scenario 8.8 — someone who consistently follows through on commitments vs. someone who doesn't could shift how skeptically a *future* promise from them specifically is treated, stored as a simple running field on `db_people.py` rather than a new subsystem.

### 25. Multi-signal proximity classification using a cheap microphone array
Rather than relying solely on ultrasonic echo-delta for bird/dog/human classification, a second cheap microphone positioned a few centimeters from the first could give crude directional/amplitude-differential information — enough to roughly triangulate which direction a sound is coming from, meaningfully improving `pet_presence.py` and `danger_detector.py`'s confidence without needing a camera at all.

### 26. Camera-based classification, replacing echo-delta guessing entirely
The single biggest perception upgrade on this list. A 13MP camera plus a lightweight on-device classifier (even a small, quantized image classification model, not a full vision-language model) would let `pet_presence.py` and `companion_context.py` answer "who's here" with actual confidence rather than proxy heuristics — this single change would meaningfully improve nearly every scenario in Sections 2–5 above.

### 27. Learning the bird's actual vocal signature, not just generic distress-loudness
`danger_detector.py`'s distress-sound check currently only checks decibel level, with a stub `_looks_like_distress_call()` that always returns true above threshold. A real implementation, using even a simple frequency-band classifier trained on the household's specific bird's actual distress vs. contentment calls, would dramatically reduce false alarms compared to loudness alone.

### 28. A shared "family calendar" awareness
If Pebble had read access to a shared household calendar (via a calendar API, not a new invented mechanism), commitments and time-awareness could cross-reference scheduled events — "you have a vet appointment for the bird tomorrow" becoming a proactively surfaced reminder rather than something only tracked if verbally promised.

### 29. Cross-device "sibling" awareness, if a second unit is ever built
If more than one Pebble-like device existed in the same household (one per room, say), a lightweight local-network protocol for sharing high-priority events (a fall, a danger alert) between units would let a companion in one room raise an alert even if the room it's in has nobody present to hear it — genuinely extending the "calling for help" concept device-to-device before it needs to leave the house entirely.

### 30. A gentle onboarding "interview" on first boot
Rather than requiring you to already know the exact phrasing patterns `entity_resolver.py` matches ("I got a bird," "her name is..."), a structured first-boot conversation ("so, who lives here with you?") could walk through populating `people/profiles.yaml` and the initial pet entities conversationally rather than requiring manual file editing before the more organic entity-resolution flow takes over.

### 31. Dream-like memory consolidation during low-activity overnight windows
Rather than consolidation running on a flat fixed interval (`memory.consolidation.run_interval_s`) regardless of time of day, scheduling the heavier consolidation pass specifically during `time_awareness.py`'s detected quiet hours — when the device is least likely to need to react to anything time-sensitive — mirrors how biological memory consolidation is understood to concentrate during rest.

### 32. A lightweight on-device wake-word, reducing always-on STT load
Currently `vad.py`'s speech/silence gate still triggers full STT on any detected utterance, whether or not it was actually directed at Pebble. A small wake-word detector (e.g., an openWakeWord or Porcupine-style lightweight model, evaluated cheaply before full STT) would let Pebble ignore ambient household conversation not addressed to it, only fully transcribing speech that starts with its name.

### 33. Explicit "do you remember when" queryability, not just spontaneous recall
Currently, memory surfaces into conversation only when the LLM's prompt context happens to include something relevant to the current trigger. A direct, explicit query path — "do you remember when the bird got into your food" — resolved via a real search over `db_episodic.py` (by tag/keyword, not full semantic search initially) rather than relying on incidental prompt inclusion, would make memory feel more reliably accessible on demand.

### 34. A physical "good job" gesture distinct from verbal praise acknowledgment
Right now `feedback.praise` only nudges mood generically. A small, distinct physical response specifically to praise — a particular RGB flourish, a specific short sound, distinct from the ordinary excited-mood palette — would make being praised feel like its own recognizable, satisfying moment rather than blending into general positive mood.

### 35. A genuinely offline-first LLM fallback with graceful capability degradation
Currently, when the local model's confidence is too low and cloud is either disabled (privacy mode) or unavailable (network outage), the fallback is simply "use the low-confidence local answer anyway." A more graceful degradation path — explicitly narrower response scope when confidence is known to be low, favoring short, honest "I'm not sure" style responses over a confident-sounding but likely-wrong generated answer — would make offline operation feel more honestly limited rather than silently worse.


---

## Speaker diarization and user separation

This section answers, with actual research behind it rather than a guess: what's the best free library for telling Pebble's household voices apart, and which one fits a resource-constrained device like this.

### The distinction that matters: verification vs. diarization

These are two different problems that get conflated often:

- **Speaker verification/identification** — "does this voice match a specific enrolled person?" This is what `voice/speaker_id.py` actually needs: a small number of known household voices (you, family members) compared against incoming audio.
- **Speaker diarization** — "how many distinct speakers are in this audio, and when does each one talk?" This is a heavier problem, typically used for transcribing meetings with multiple unknown participants. Pebble doesn't need this in its current design — it needs verification against a small known set, not open-ended diarization.

Getting this distinction right matters because the diarization-focused libraries (pyannote.audio, Diart) are considerably heavier than what a verification-only use case actually requires.

### Option 1 — Resemblyzer (recommended starting point)

**License:** Apache 2.0 (fully free, no usage restrictions) · **What it does:** derives a 256-value embedding vector from a few seconds of speech, then compares embeddings via cosine similarity.

This is the closest match to what `speaker_id.py` is already architected to do — `_match_voiceprint()` is designed around exactly this shape: compute an embedding, compare against enrolled `.npy` files, threshold on similarity. Resemblyzer needs only 5–30 seconds of enrollment audio per person (matching `voice.speaker_id.enroll_min_samples` in config almost exactly), and its model is small enough to run comfortably on a Raspberry Pi without a GPU.

```bash
pip install resemblyzer
```

```python
from resemblyzer import VoiceEncoder, preprocess_wav
encoder = VoiceEncoder()
wav = preprocess_wav("nigam_sample.wav")
embedding = encoder.embed_utterance(wav)   # 256-d vector, save as .npy
# later, compare via cosine similarity against stored embeddings
```

**Recommendation: use this to fill in `speaker_id.py`'s stubs.** It's the lightest option, free, and matches the existing code's shape almost exactly — the least amount of rework to go from stub to live.

### Option 2 — SpeechBrain (ECAPA-TDNN), for higher accuracy at higher cost

**License:** Apache 2.0 · **What it does:** a full speech-processing toolkit; the specific pretrained model relevant here is `speechbrain/spkrec-ecapa-voxceleb`, a state-of-the-art speaker-embedding model trained on the VoxCeleb dataset.

This is measurably more accurate than Resemblyzer (published Equal Error Rate around 0.8% on VoxCeleb1-test), but it's a heavier PyTorch-based dependency and a bigger model to run continuously on constrained hardware. Notably, a real published IoT research paper describes exactly this system — SpeechBrain for speaker ID, paired with Silero/WebRTC VAD and Whisper for STT — running on a Raspberry Pi for local, offline audio processing, which is a strong practical validation that this stack works on comparable hardware to what Pebble targets.

```bash
pip install speechbrain torchaudio
```

```python
from speechbrain.inference import EncoderClassifier
classifier = EncoderClassifier.from_hparams(source="speechbrain/spkrec-ecapa-voxceleb")
embeddings = classifier.encode_batch(signal)
```

**Recommendation: upgrade path if Resemblyzer's accuracy proves insufficient** in practice (e.g., too many false stranger-detections of actual family members, or vice versa) — don't start here, since the accuracy gain may not be worth the heavier runtime cost for a small household voice set.

### Option 3 — pyannote.audio, for full diarization if ever needed

**License:** MIT · **Stats:** 9,600+ GitHub stars, actively maintained, published in real academic research pipelines.

This is the strongest, most complete answer if Pebble's needs ever grow beyond "match against a small known set" into genuine open-ended diarization — for instance, if you wanted a "how many different people were in the room today, and roughly how much did each talk" feature. It requires downloading a pretrained model from Hugging Face (a free account and accepting model terms, not a paid tier) and is noticeably heavier to run than Resemblyzer.

**Recommendation: not needed for Pebble's current design.** Worth knowing about if the scope ever expands toward genuine multi-speaker meeting-style transcription, but pure verification against enrolled household voices doesn't need this much machinery.

### Option 4 — Diart, for real-time streaming diarization specifically

**License:** MIT · Published in the Journal of Open Source Software (2024), built on top of pyannote's models but optimized specifically for real-time/streaming use rather than offline batch processing.

Relevant only if a future version of Pebble needs to diarize a continuous, ongoing audio stream (rather than discrete VAD-gated utterances, which is how `vad.py` currently works) — for Pebble's current utterance-by-utterance design, this is more machinery than needed.

### The actual recommendation for `speaker_id.py`

1. Start with **Resemblyzer** for both enrollment (`enroll()`) and matching (`_match_voiceprint()`) — smallest, free, fits the existing code shape.
2. Store embeddings as `.npy` files under `people/voiceprints/{person_key}.npy`, exactly as the current docstring already describes.
3. If accuracy proves insufficient with your household's actual voices, upgrade the embedding model to **SpeechBrain's ECAPA-TDNN** — a real, proven Raspberry Pi deployment pattern exists for this exact combination.
4. Don't reach for pyannote.audio or Diart unless the scope genuinely grows into open-ended multi-speaker diarization, which isn't what this project currently needs.

---

## Bluetooth and external audio

### Why "play on the bedroom speaker" and "play on my phone" are different problems

A Bluetooth speaker is designed to be a **sink** — it passively accepts an audio stream from whatever's currently connected to it, the same way your phone already streams to it. Your phone, by contrast, is normally a **source** — it pushes audio out, it doesn't have a standard mechanism for accepting an incoming push from some other nearby device on demand. There's no standard Bluetooth flow for "hey phone, play this audio some other gadget is sending you" the way there is for a dedicated speaker.

**Practical consequence:** "stream music to the bedroom speaker" is a real, well-supported thing to build. "Push audio directly onto my phone" isn't a standard capability — the honest path there is a push notification (ntfy/Telegram) prompting you to play something yourself, not Pebble directly injecting audio into your phone's speaker.

### Why the ESP32 needs to be a bridge, not the whole pipeline

The ESP32 has genuine built-in Bluetooth Classic support with A2DP (Advanced Audio Distribution Profile) — the exact protocol phones use to stream to speakers — and can act as an **A2DP source**, meaning it can initiate a connection to a speaker and push audio to it, exactly like a phone would. The `ESP32-A2DP` library (by pschatzmann) wraps this cleanly for Arduino-style development.

The honest constraint: decoding compressed audio (MP3/AAC into raw PCM) **and** running Bluetooth A2DP simultaneously is a genuinely heavy load for a bare ESP32. The architecturally sound split, and the one `body/bluetooth_audio_out.py` is designed around, is:

```
yt-dlp resolves + downloads audio  (on the Pi / "brain" device)
       ↓
audio decoded to raw PCM            (on the Pi / "brain" device)
       ↓
PCM streamed over local WiFi        (Python → ESP32, via a small TCP socket)
       ↓
ESP32 forwards over Bluetooth A2DP  (ESP32 firmware, separate codebase)
       ↓
bedroom speaker plays it
```

This keeps the ESP32's job narrowly scoped to "receive PCM, forward over Bluetooth" — the thing it's actually well-suited for — rather than asking it to also do the heavier decode work a more capable device already handles better.

### What's real vs. what needs separate firmware work

`body/bluetooth_audio_out.py` (the Python side) is a real, if stubbed, module — it defines the streaming contract (chunk size, target host/port, per-speaker config) and the failure-handling path (falls back gracefully if the ESP32 bridge is unreachable, rather than silently going nowhere). What it does **not** include, and what's explicitly out of scope for this Python codebase, is the actual ESP32 firmware — a separate C++/Arduino-toolchain project that would need to be flashed onto the ESP32 itself, handle WiFi connection, open the receiving socket, and forward received PCM into `ESP32-A2DP`'s source callback. That firmware is a distinct deliverable, written and tested against real ESP32 hardware, not something derivable purely from the Python side.

### Recommended build order

Get the core audio pipeline (TTS actually speaking, music actually playing) working through whatever's simplest first — even a basic wired speaker directly on the Pi/brain device, no Bluetooth at all — before adding the ESP32 bridge as a later upgrade. Debugging a proven core audio pipeline plus a new Bluetooth pairing layer simultaneously is much harder than proving each independently.


---

## Placeholder and stub audit

Every function below currently returns a hardcoded stub value, does nothing, or is marked with a `# SENSOR INPUT HOOK` comment. This is the complete, file-by-file list of exactly what needs real code before Pebble runs against real hardware and real data instead of mocks. Organized by subsystem, in the order you'd realistically want to tackle them.

**How to use this list:** each entry names the file, the function, what it currently does (the stub behavior), and what real implementation needs to replace it. Nothing here requires architectural changes — every hook is a drop-in replacement inside an existing function signature.

### Sensors — real hardware reads

| File | Function | Current stub behavior | What real code needs to do |
|---|---|---|---|
| `sensors/pir.py` | `_read_pin()` | Always returns `False` | Real GPIO digital read on `self.cfg["pin"]`, via `RPi.GPIO` or `gpiozero` |
| `sensors/ultrasonic.py` | `_measure_distance_cm()` | Always returns `None` | Real trigger/echo pulse timing on `self.cfg["trigger_pin"]` / `self.cfg["echo_pin"]`, converting round-trip time to distance |
| `sensors/mpu6050.py` | `_read_imu()` | Always returns `(None, None)` | Real I2C read from `self.cfg["i2c_address"]` via `smbus2` or similar, returning combined acceleration (g) and tilt (degrees from level) |
| `sensors/dpdt_mode_switch.py` | `_read_switch()` | Always returns `False` | Real GPIO digital read on `self.cfg["pin"]` |
| `sensors/danger_detector.py` | `_looks_like_distress_call(freq_hz)` | Always returns `True` above the dB threshold | A real frequency-band classifier distinguishing the household's specific bird's distress calls from routine chirps — see future idea #27 |
| `sensors/danger_detector.py` | `_on_sound` subscription | Never wired — `sensor.sound_event` topic doesn't exist yet | A real microphone amplitude/FFT reader publishing `{db, freq_hz}` on this topic |

### Power — real ADC read

| File | Function | Current stub behavior | What real code needs to do |
|---|---|---|---|
| `power/power_manager.py` | `_read_battery_voltage()` | Returns `None` unless `_mock_battery` is set | Real ADC read on `self.cfg["battery_adc_channel"]`, converting raw ADC value to voltage based on your specific voltage divider circuit |

### Voice — real models and audio I/O

| File | Function | Current stub behavior | What real code needs to do |
|---|---|---|---|
| `voice/vad.py` | `_read_audio_frame()` | Returns `None` | Real microphone frame capture via `pyaudio` or `sounddevice`, sized to `self.cfg["frame_ms"]` |
| `voice/vad.py` | `_classify_frame(frame)` | Always returns `False` | Real VAD classification via `webrtcvad`, respecting `self.cfg["aggressiveness"]` |
| `voice/stt_whisper.py` | `_ensure_model_loaded()` | Sets `self._model = "stub-loaded"` | Real model load via `faster-whisper`, sized per `self.cfg["model_size"]` on `self.cfg["device"]` |
| `voice/stt_whisper.py` | `_transcribe(audio_bytes)` | Always returns `""` | Real Whisper inference call on the captured audio buffer |
| `voice/speaker_id.py` | `_load_enrolled_voiceprints()` | Sets each entry to `None` | Real embedding load from `.npy` files — see [speaker diarization section](#speaker-diarization-and-user-separation) for library choice |
| `voice/speaker_id.py` | `_match_voiceprint(audio_bytes)` | Always returns `(None, 0.0)` | Real embedding extraction + cosine-similarity nearest-neighbor match against `self._enrolled_voiceprints` (Resemblyzer, per the recommendation above) |
| `voice/speaker_id.py` | `enroll(person_key, audio_samples)` | Returns `True`/`False` based only on sample count, computes nothing | Real embedding computation and `.npy` save to `self._voiceprint_dir / f"{person_key}.npy"` |
| `voice/tts_edge.py` | `_resolve_voice(person_key)` | Always returns the config default | Real lookup into `people/profiles.yaml`'s per-person `tts_voice` field |
| `voice/tts_edge.py` | `_synthesize_and_play(text, voice)` | Does nothing | Real `edge-tts` synthesis call plus audio playback (e.g., via `simpleaudio`, `sounddevice`, or piping to `ffplay`) |
| `voice/amp_controller.py` | `_apply_hardware_volume(volume)` | Does nothing | Real amplifier gain control — either an I2C-controlled amp chip (e.g., MAX9744) or software gain scaling applied to the PCM buffer before playback |
| `voice/music_player.py` | `_resolve_and_download(query)` | Returns a hardcoded stub path, never actually invokes `yt-dlp` | Real `subprocess.run(["yt-dlp", ...])` call, then locating the resulting downloaded file |
| `voice/music_player.py` | `_play_audio_file(path)` | Does nothing | Real audio playback of the downloaded file, ideally routed through `amp_controller.py`'s volume path |
| `voice/music_player.py` | `_stop_playback()` | Does nothing | Real playback-stop call to whatever player is handling `_play_audio_file` |

### Body — real display and motor output

| File | Function | Current stub behavior | What real code needs to do |
|---|---|---|---|
| `body/face/oled_driver.py` | `init()` | Falls back to `MockDisplay` unconditionally | Real display init via `luma.oled` (SSD1306/SSH1106) on `self.cfg["i2c_address"]`, with a genuine hardware/mock branch based on `COMPANION_MOCK_HARDWARE` |
| `body/face/oled_driver.py` | `draw_sprite_sequence(sprite_path)` | Calls `MockDisplay.show_placeholder()` | Real frame-by-frame blit from actual sprite image assets — **note: the sprite assets themselves (`body/face/sprites/`) don't exist yet either; this needs both real code AND real art** |
| `body/face/oled_driver.py` | `draw_privacy_indicator()` | Calls `MockDisplay.show_placeholder()` | Real privacy-indicator rendering |
| `body/rgb_visualizer.py` | `_init_strip()` | Returns `None` | Real LED strip init via `rpi_ws281x` on `self.cfg["pin"]` with `self.cfg["led_count"]` |
| `body/rgb_visualizer.py` | `_set_strip_color(color_hex, brightness)` | Does nothing | Real LED strip color write |
| `body/seven_segment.py` | `_init_device()` | Always returns a `MockDisplay` | Real I2C init via an HT16K33-based seven-segment driver on `self.cfg["i2c_address"]` |
| `body/vibration_motor.py` | `_set_motor_intensity(intensity)` | Does nothing | Real PWM duty-cycle write to the motor driver pin, scaled by `intensity` in `[0.0, 1.0]` |
| `body/bluetooth_audio_out.py` | `_stream_to_bridge(pcm_bytes, host, port)` | Does nothing | Real TCP socket streaming to the separate ESP32 firmware bridge — see the [Bluetooth section](#bluetooth-and-external-audio) for the full explanation of why this needs separate firmware work too |

### Brain — LLM and reasoning integrations

| File | Function | Current stub behavior | What real code needs to do |
|---|---|---|---|
| `brain/local_llm.py` | `_ensure_loaded()` | Sets `self._model = "stub-loaded"` | Real model load via `llama-cpp-python` from `self.cfg["model_path"]` |
| `brain/local_llm.py` | `generate(prompt)` | Returns a fixed stub string with `confidence=0.5` | Real inference call, respecting `max_tokens`, `temperature`, `timeout_s` from config |
| `brain/gemini_client.py` | `_ensure_client()` | Sets `self._client = "stub-client"` | Real Gemini SDK client init using `self._api_key` and `self.cfg["model"]` |
| `brain/gemini_client.py` | `generate(prompt)` | Returns a fixed stub string | Real API call, respecting the same config parameters |

### Network — messaging and remote access

| File | Function | Current stub behavior | What real code needs to do |
|---|---|---|---|
| `network/messenger.py` | `_send_telegram(person_key, text)` | Returns `True` without sending anything | Real `POST https://api.telegram.org/bot{token}/sendMessage` call with `{chat_id, text}` |
| `network/messenger.py` | `_send_twilio_sms(person_key, text)` | Returns `True` without sending anything | Real call via the official `twilio` Python SDK: `Client(sid, token).messages.create(...)` |
| `network/messenger.py` | `_send_ntfy(person_key, text)` | Not yet added — needs to be added to the provider branch | Real `POST https://ntfy.sh/{topic}` with the message as the request body, no auth needed |
| `network/remote_bridge.py` | `_init_server()` | Returns `None` | Real HTTP/WebSocket server bind on `self.cfg["host"]:self.cfg["port"]`, routing authenticated requests to `_handle_command` |
| `network/connection_watchdog.py` | `_ping(host)` | Always returns `True` | Real reachability check — a socket connect attempt or ICMP ping to `host` |

### Configuration gaps to close before boot succeeds

These aren't code stubs — they're config blocks that were designed during this project's development but may not yet exist in your actual `config.yaml` file on disk, depending on which changes you've applied. Cross-check each of these sections exists before assuming a `KeyError` means a code bug rather than a missing config block:

- `time_awareness` (timezone, quiet hours, stale-clock threshold)
- `memory_worth` (trauma topic list, retention override, funny-moment threshold)
- `danger_escalation` (proximity/sound thresholds, escalation stage timing)
- `commitment_watchdog` (check interval, re-nag interval, grace period)
- `memory.commitments`, `memory.entities`, `memory.open_questions` (database paths for each new store)
- `entity_resolver` (re-ask timing)
- `companion_context` (voice-signal trust window)
- `sensors.pet_presence.human_min_echo_delta_cm` and `human_motion_confidence_min` (the human-classification extension)
- `messaging` (provider selection and per-person contact targets)
- `music` (search provider, cache settings)
- `body.vibration` (pin, pattern definitions)
- `voice.amp` (baseline/whisper/max volume levels)

### `.env` values that need to be filled in, not just present

| Variable | Needed for | Where to get it |
|---|---|---|
| `GEMINI_API_KEY` | Cloud LLM fallback | Google AI Studio |
| `REMOTE_BRIDGE_TOKEN` | Authenticating remote dashboard commands | Any securely generated random string you choose |

### Files that are structurally complete stubs — entire modules, not just functions

These files exist purely as dev-mode stand-ins and are **intentionally** never meant to be "filled in" — they're the mock/fallback path, not a placeholder for real logic:

- `sensors/mock_sensors.py` — intentional synthetic sensor noise generator for development
- `power/mock_power.py` — intentional simulated battery drain curve for development
- `body/mock_display.py` — intentional dev-mode display stand-in, logs instead of rendering

### Assets that don't exist yet at all (not code — art/data)

- `body/face/sprites/` — referenced by `oled_driver.py` and `animator.py`, but no actual sprite image files exist in this directory yet. Every mood needs at minimum an idle sequence (`idle_curious`, `idle_bored`, `idle_annoyed`, `idle_sleepy`, `idle_excited`) plus each reflex-triggered overlay expression (`startled`, `curious_glance`, `watch_bird`, `acknowledge_dog`, `mode_change_ack`, `pointed_reminder`, `curious_question`, `tired_and_worried`, `panicked_low_power`).
- `people/voiceprints/` — empty until real enrollment (via `speaker_id.py`'s `enroll()`, once implemented) actually happens against real household voices.

---

← Back to [README.md](./README.md) · [KNOWLEDGE.md](./KNOWLEDGE.md) · [Back to top](#pebble--full-capability-catalog)