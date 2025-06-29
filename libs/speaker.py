import pygame
import time

import yaml

with open("/home/pi/src/couch/libs/sounds.yaml", "r") as f:
    SOUNDS = yaml.safe_load(f)

def play_music(music_file: str):
    if music_file not in SOUNDS:
        raise ValueError(f"Sound file {music_file} not found")

    pygame.mixer.init()
    pygame.mixer.music.load(SOUNDS[music_file])

    pygame.mixer.music.play()

    while pygame.mixer.music.get_busy():
        time.sleep(0.1)
