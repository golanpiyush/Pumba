#!/usr/bin/env python3
"""
scaffold_kiko.py — Creates the Kiko companion project structure
A physical AI pet-companion that lives with a bird and dog.
"""

import os
from pathlib import Path

def create_structure():
    """Create the exact folder/file structure for Kiko."""
    
    # Define the structure
    structure = {
        "companion": {
            "main.py": None,
            "config.yaml": None,
            ".env": None,
            "prompts": {
                "core_identity.md": None,
                "personality_quirks.md": None,
                "mood": {
                    "curious.md": None,
                    "bored.md": None,
                    "annoyed.md": None,
                    "sleepy.md": None,
                    "excited.md": None,
                },
                "modes": {
                    "normal.md": None,
                    "debug.md": None,
                    "privacy.md": None,
                },
                "people": {
                    "nigam.md": None,
                    "family_default.md": None,
                    "stranger.md": None,
                },
                "pets": {
                    "dog.md": None,
                    "bird.md": None,
                },
                "response_rules.md": None,
            },
            "brain": {
                "personality.py": None,
                "mood_engine.py": None,
                "operating_mode.py": None,
                "llm_router.py": None,
                "local_llm.py": None,
                "gemini_client.py": None,
                "prompt_builder.py": None,
                "inspector": {
                    "fact_inspector.py": None,
                    "relevance_scorer.py": None,
                    "contradiction_check.py": None,
                    "response_inspector.py": None,
                },
            },
            "memory": {
                "db_semantic.py": None,
                "db_episodic.py": None,
                "db_people.py": None,
                "memory_manager.py": None,
            },
            "voice": {
                "stt_whisper.py": None,
                "speaker_id.py": None,
                "tts_edge.py": None,
                "vad.py": None,
            },
            "body": {
                "face": {
                    "sprites": {},  # Directory for sprite files
                    "animator.py": None,
                    "oled_driver.py": None,
                },
                "rgb_visualizer.py": None,
                "seven_segment.py": None,
                "mock_display.py": None,
            },
            "sensors": {
                "sensor_bus.py": None,
                "pir.py": None,
                "ultrasonic.py": None,
                "mpu6050.py": None,
                "dpdt_mode_switch.py": None,
                "pet_presence.py": None,
                "mock_sensors.py": None,
            },
            "power": {
                "power_manager.py": None,
                "modes.py": None,
            },
            "network": {
                "remote_bridge.py": None,
                "connection_watchdog.py": None,
            },
            "people": {
                "voiceprints": {},  # Directory for voiceprint files
                "profiles.yaml": None,
            },
            "tests": {},  # Directory for test files
            "logs": {},  # Directory for log files
        }
    }
    
    def create_recursive(base_path, structure_dict):
        """Recursively create directories and files."""
        for name, content in structure_dict.items():
            path = base_path / name
            if content is None:
                # It's a file
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            elif isinstance(content, dict):
                # It's a directory
                path.mkdir(parents=True, exist_ok=True)
                if content:  # If not empty, recurse
                    create_recursive(path, content)
            else:
                # Shouldn't happen, but just in case
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
    
    # Create the structure
    create_recursive(Path("."), structure)
    
    # Create .gitkeep files in empty directories
    for dirpath, dirnames, filenames in os.walk("companion"):
        if not dirnames and not filenames:
            gitkeep = Path(dirpath) / ".gitkeep"
            gitkeep.touch()
    
    print("✨ Kiko's home is ready!")
    print(f"📁 Created structure at: {Path('companion').resolve()}")
    
    # Count files created
    file_count = sum(1 for _, _, files in os.walk("companion") for f in files if f != ".gitkeep")
    print(f"📄 Created {file_count} files (plus .gitkeep placeholders)")
    print("\n🏠 Kiko is waiting to be brought to life!")
    print("   Next: Run python companion/main.py to see Kiko wake up")

if __name__ == "__main__":
    create_structure()