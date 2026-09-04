# 20 Ideas Worth Building (Beyond the Scaffold)

Ranked roughly by "how much personality-per-line-of-code" they deliver.
None of these are generic chatbot features — each one leans on the fact
that this thing has a body, lives in one place, and has neighbors.

1. **Cage-relative spatial memory.** Instead of one blob of "episodic
   memory," let it build a rough mental map of the cage — "the corner near
   the water dish," "the swing side." Incidents tagged with a zone let it
   say "you always do this near the swing" instead of vague generalities.

2. **Bird mood mirroring, inverted.** If the bird's been agitated (lots of
   motion/sound) for a while, Pebble gets *more* watchful/protective, not
   just more stimulated — arousal from the bird's activity should route
   partly into a distinct "guardian" sub-state, not just generic excitement.

3. **A "tattling" instinct with a cooldown.** If the dog does something
   near the cage while Nigam is nearby (person_recognized recently), it's
   funnier and more alive if Pebble narrates it live ("hey — the dog's
   sniffing at the cage again") rather than just logging it silently. Rate
   limit hard so it doesn't cry wolf.

4. **Sleep schedule inference, not a timer.** Rather than a fixed bedtime,
   let memory_manager.py notice the actual household's quiet-hours pattern
   over weeks and have mood_engine's baseline arousal dip automatically
   during that window — its "circadian rhythm" is learned, not configured.

5. **Distinct alarm calls per danger type.** A wire-chewing alert, a fall,
   and a stranger-at-the-door event should never sound the same. Give the
   RGB/face/voice a small distinct "vocabulary" of 3–4 alarm patterns so a
   human across the room can distinguish severity/type without looking.

6. **A grudge that fades.** When contradiction_check.py or scold events
   happen, let a *temporary* negative modifier attach to a specific
   subject (e.g. "annoyed at the dog specifically") that decays
   independently from general mood — so it can be sleepy-but-still-huffy
   at one specific housemate.

7. **First-of-its-kind excitement.** The very first time a new pattern is
   detected (memory.pattern_detected fires for a *new* subject/predicate
   pair), let personality.py treat that specifically as a small "excited"
   mood spike — noticing something new about a housemate is a big deal
   the first time, mundane by the tenth.

8. **Physical "flinch away" motor reflex,** if you ever add a servo/wheel
   base: for true reflex-tier events (fall, loud bang) the instinct layer
   could trigger a tiny physical flinch/backup motion, not just a face/LED
   change — closing the loop between "startled" and an actual body
   reaction.

9. **Voice-print onboarding as a mini-ritual,** not a settings menu. When
   speaker_id.py fails to match someone repeatedly, have Pebble get
   "curious enough" to prompt an enrollment conversationally ("you keep
   showing up and I don't know your voice yet") instead of a silent admin
   flow.

10. **Weather/light-level correlation with mood baseline.** A cheap light
    sensor correlated over weeks with observed activity level could let
    Pebble develop a "grumpy on dark mornings" pattern — genuinely
    creature-like without needing any LLM reasoning to produce it.

11. **A private "diary" only spoken in privacy mode.** Ironically, privacy
    mode could be when Pebble is *most* willing to muse out loud (since
    nothing's persisted) — a small opportunity for more unguarded,
    personality-forward lines specifically gated to that mode.

12. **Escalating "calling for help" stages.** Rather than one flat alarm
    behavior on fall/disconnection, define 2–3 escalating stages (chirp →
    louder distress pattern → final "SOS" loop) tied to how long the
    unresolved state has persisted — mirrors how a real animal's distress
    intensifies.

13. **Environment-aware volume/brightness.** Use the ambient light/noise
    baseline (from PIR/mic activity patterns) to auto-scale RGB brightness
    and TTS volume, so it isn't jarringly loud/bright in a quiet room at
    2am even without an explicit night mode.

14. **A running "bird logbook" it can narrate.** Once enough episodic data
    accumulates, add a lightweight local-only summarizer (no cloud call
    needed) that can answer "how's the bird been lately" by pulling
    recent notable bird-tagged episodes — a natural, low-cost use of
    local_llm.py.

15. **Cross-checked fall vs. "being picked up."** Distinguish an actual
    fall/drop from a gentle pickup using the MPU6050's acceleration
    *profile* (a real fall is a sharp, short spike; being lifted is a
    smoother sustained change) so it doesn't panic every time someone
    picks it up affectionately.

16. **Territorial "opinion drift" toward the dog.** Let the confidence on
    dog-related semantic facts specifically require *more* repeats to
    solidify than bird-related ones (dog encounters are noisier/less
    consistent), so its "opinions" about the dog feel earned rather than
    snap judgments — configurable per-subject in
    memory.consolidation.min_repeats_for_pattern.

17. **A boredom-triggered self-initiated event.** When bored mood persists
    past a threshold with no new events, let it occasionally initiate
    something small unprompted (a soft sound, an idle animation change) —
    the difference between a device that waits to be triggered and one
    that has its own idle behavior.

18. **Contextual quietness around sleeping animals.** If pet_presence.py
    infers the bird has been still for an unusually long stretch during
    its normal-active hours, treat that specially — either "probably
    asleep, stay quiet" or, after enough repetition without explanation,
    flag it as worth a person's attention (an old/unwell bird pattern).

19. **A "proud" reaction to being praised in front of someone.** If a
    praise event happens while person_recognized is also fresh for a
    *different* person than usual, let excited mood spike slightly higher
    — showing off in front of company is a very pet-like, very specific
    behavior a flat praise-event delta wouldn't capture.

20. **Seasonal/anniversary callbacks.** Since episodic memory is
    timestamped, a once-a-year job could resurface "this is around when
    [notable incident] happened" — a small, low-effort way to make the
    "grows over time" requirement viscerally obvious to the people living
    with it, rather than only inferable from behavior.