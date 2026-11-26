#!/usr/bin/env python3
"""Write dist/mindseeker_script.csv (every translated line) and dist/mindseeker_jp.tbl."""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build
import screens
from jp_table import build_script_table

ROOT = Path(__file__).resolve().parent.parent

# Menu and screen text, translated by hand: (where, Japanese, literal, final).
SCREEN_ROWS = [
    ("CHR bank $47 (file 0x31C10), new-game prompt",
     "まえのデータをけして\nあらたにゲームをはじめますか？",
     "Erase the previous data and start a new game?", "Erase old data\nand start over?"),
    ("CHR bank $47, choices", "いいえ / はい", "No / Yes", "NO / YES"),
    ("PRG bank 7 +0000, name entry title", "なまえとうろく", "Name registration", "Name"),
    ("PRG bank 7 +0000, name entry", "プレイヤー", "Player", "Player"),
    ("PRG bank 7 +0000, name entry", "とうろくしゅうりょう", "Finish registration", "Finish"),
    ("PRG bank 7 +0000, name entry", "メッセージスピードせってい", "Message speed setting",
     "Text Speed"),
    ("PRG bank 7 +0000, name entry", "もどる / おわる", "Go back / End", "Back / End"),
    ("PRG bank 7 +0000, name entry grid", "あいうえお … (kana grid)", "(kana table)",
     "A-Z, a-z and . ' \" - ! ?"),
    ("PRG bank 7 +0206, speed box title", "メッセージスピード", "Message speed", "Text Speed"),
    ("PRG bank 7 +028C, rename prompt", "なまえを　とうろく　しなおしますか？",
     "Register the name again?", "Change your name?"),
    ("PRG bank 7 +028C, choices", "いいえ / は　い", "No / Yes", "NO / YES"),
    ("PRG bank 7 +1D8E, ending saying 1",
     "うちゅう　は　バランス　のみだ。\nそこに　ふかさとしての　リズム　がある。",
     "The universe is only balance. In it there is rhythm, as depth.",
     "The universe is balance,\nwith rhythm as its depth."),
    ("PRG bank 7 +1DCB, ending saying 2",
     "くうかん　が　そくど　を　もつのであって\nひかり　が　そくど　を　もつのではない。",
     "It is space that has speed; it is not light that has speed.",
     "Space is what has speed.\nLight itself has none."),
    ("PRG bank 7 +1E18, ending saying 3",
     "ぶっしつ　は　ひかり　を　めざし\nひかり　は　ぶっしつ　を　うみつづける。",
     "Matter aims for light, and light goes on giving birth to matter.",
     "Matter reaches for light.\nLight creates matter anew."),
    ("PRG bank 7 +1E63, ending saying 4",
     "せいめい　も　うちゅう　も\nぜんたいとして　じぞくしている。",
     "Both life and the universe persist as a whole.",
     "Life and the universe\nendure as one whole."),
    ("PRG bank 7 +1E94, ending saying 5", "そんざい　とは　ちょっかん　の　だいめいしである。",
     "Existence is a byword (pronoun) for intuition.", "Existence is another\nname for intuition."),
    ("PRG bank 7 +1EC8, ending saying 6", "げんご　は　はどう　の　ていちゃくである。",
     "Language is the fixing (settling) of waves/vibration.",
     "Words are vibrations\nthat have settled."),
    ("CHR banks $42-$43 (file 0x30810), title attract text",
     "このソフトは　あなたの　せんざいいしきの\nなかに　ねむっている　サイキックパワーを\n"
     "ひきだすために　かいはつされた、\nちょうのうりょくかいはつソフトです。\n"
     "エスパーキヨタの　たいけんに　もとづいて\nげんみつに　シミュレートしているので\n"
     "あなたの　マインドレベル　にあわせて\nトレーニングを　すすめれば　かならず\n"
     "あなたも　ちょうのうりょくしゃに\nなれるでしょう……。",
     "This software is psychic-development software, developed to draw out the psychic "
     "power sleeping in your subconscious. It simulates strictly, based on Esper Kiyota's "
     "experience, so if you advance the training to suit your Mind Level, you too will "
     "surely become a psychic...",
     "This software was made\nto awaken the psychic\npower sleeping deep in\nyour subconscious.\n"
     "It is closely modeled\non Esper Kiyota's own\nexperience. Train at\nyour Mind Level, and\n"
     "you too will surely\nbecome a psychic…"),
]

# Japanese behind each panel label, in the order of screens.PANEL_LISTS: (Japanese, literal).
PANEL_JAPANESE = {
    "YES": ("はい", "Yes"),
    "NO ": ("いいえ", "No"),
    "YES NO ": ("はい　　いいえ", "Yes / No"),
    "Inhale": ("すって………", "Breathe in..."),
    "Hold… ": ("とめて………", "Hold it..."),
    "Exhale": ("はいて………", "Breathe out..."),
    "MAP": ("まっぷ", "Map"),
    "GUIDE": ("しせつない", "Facility guide"),
    "EXAM": ("けんてい", "Certification exam"),
    "TRAIN": ("トレーニング", "Training"),
    "TRIP": ("トリップ", "Trip (Mind Trip)"),
    "CLAIR.": ("とうし", "Clairvoyance"),
    "PK": ("ねんりき", "Psychokinesis"),
    "PRECOG": ("よち", "Precognition"),
    "SET": ("せっと", "Set"),
    "FORM": ("しせい", "Posture"),
    "BREATH": ("こきゅう", "Breathing"),
    "IMAGE": ("いめーじ", "Image / visualization"),
    "USE": ("つかう", "Use"),
    "DON'T": ("つかわない", "Don't use"),
    "INFO": ("じょうほう", "Information"),
    "RECORD": ("きろく", "Record"),
    "MEDIT.": ("めいそう", "Meditation"),
    "SAVE": ("せーぶ", "Save"),
    "DATA": ("でーた", "Data"),
    "RACE": ("れーす", "Race"),
    "CARD": ("かーど", "Card"),
    "PANEL": ("ぱねる", "Panel"),
}




def token_text(text):
    return text.replace("<N><N><N><N>", "{NAME}").replace("<V>", "{V}").replace("<END>", "")


def main():
    dump = json.loads((ROOT / "script" / "dialogue_jp.json").read_text())
    english = build.load_translations()
    rows = []
    for string in dump["strings"]:
        if string["id"] in build.NOT_TEXT:
            continue
        entry = english[string["id"]]
        where = (f"{string['id']} (file 0x{string['file_offset']:05X}, "
                 f"PRG bank {string['bank']} ${string['cpu']:04X})")
        rows.append((where, token_text(string["text"]), entry.get("literal", ""),
                     build.normalize(entry["final"])))
    rows.extend(SCREEN_ROWS)
    for bank, offset, records in screens.PANEL_LISTS:
        for address, text in records:
            japanese, literal = PANEL_JAPANESE[text]
            rows.append((f"PRG bank {bank} +{offset:04X}, panel label at PPU ${address:04X}",
                         japanese, literal, text.strip()))
    for token, word in sorted(build.WORD_TOKENS.items()):
        japanese = {3: "とうし", 4: "ねんりき", 5: "よち"}[token]
        rows.append((f"power-name tables (PRG banks 2, 6, 9), value token {token}",
                     japanese, word, word))

    dist = ROOT / "dist"
    with open(dist / "mindseeker_script.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["offset / scene id", "original Japanese", "literal translation", "final English"])
        writer.writerows(rows)

    table = build_script_table()
    lines = ["00=\\n", "10={NAME letter}", "F0={V}", "FF={END}"]
    lines += [f"{code:02X}={char}" for code, char in sorted(table.items())
              if code not in (0x00, 0x10, 0xF0, 0xFF)]
    (dist / "mindseeker_jp.tbl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(rows)} rows")


if __name__ == "__main__":
    main()
