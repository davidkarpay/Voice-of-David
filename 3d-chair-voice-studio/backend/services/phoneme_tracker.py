"""Phoneme coverage tracking using the CMU Pronouncing Dictionary (cmudict).

Tracks which of the 39 ARPAbet phonemes have been covered by recorded
sentences, identifies gaps, and provides coverage statistics.

ARPAbet is a phonetic transcription system developed at Carnegie Mellon
University (CMU) that maps English words to a set of phoneme symbols.
"""

import json
import re
from typing import Optional

# ARPAbet phoneme inventory grouped by category
PHONEME_CATEGORIES = {
    "plosive": ["P", "B", "T", "D", "K", "G"],
    "affricate": ["CH", "JH"],
    "fricative": ["F", "V", "TH", "DH", "S", "Z", "SH", "ZH", "HH"],
    "nasal": ["M", "N", "NG"],
    "liquid": ["L", "R"],
    "semivowel": ["W", "Y"],
    "vowel": [
        "AA", "AE", "AH", "AO", "AW", "AX", "AY",
        "EH", "ER", "EY",
        "IH", "IY",
        "OW", "OY",
        "UH", "UW",
    ],
}

# Flatten to a set of all phonemes
ALL_PHONEMES = set()
PHONEME_TO_CATEGORY = {}
for category, phonemes in PHONEME_CATEGORIES.items():
    for p in phonemes:
        ALL_PHONEMES.add(p)
        PHONEME_TO_CATEGORY[p] = category

# Embedded subset of CMU dictionary for common words
# In production, we load the full cmudict via nltk
_cmudict = None


def _load_cmudict() -> dict:
    """Load CMU Pronouncing Dictionary via nltk, with rule-based fallback."""
    global _cmudict
    if _cmudict is not None:
        return _cmudict

    try:
        import nltk
        try:
            from nltk.corpus import cmudict
            _cmudict = cmudict.dict()
            return _cmudict
        except LookupError:
            try:
                nltk.download("cmudict", quiet=True)
                from nltk.corpus import cmudict
                _cmudict = cmudict.dict()
                return _cmudict
            except Exception:
                pass
    except Exception:
        pass

    # Fallback: rule-based approximate phoneme mapping
    _cmudict = _build_rule_based_dict()
    return _cmudict


def _build_rule_based_dict() -> dict:
    """Build a simple rule-based phoneme dictionary for common English words.

    This is a fallback when nltk/cmudict is unavailable. It maps common letter
    patterns to ARPAbet phonemes. Not as accurate as cmudict but covers the
    most frequent English words.
    """
    # Map common words to their approximate ARPAbet pronunciations
    # This covers the ~500 most common English words
    words = {
        "the": [["DH", "AH0"]], "a": [["AH0"]], "an": [["AE1", "N"]],
        "and": [["AE1", "N", "D"]], "of": [["AH1", "V"]], "to": [["T", "UW1"]],
        "in": [["IH1", "N"]], "is": [["IH1", "Z"]], "it": [["IH1", "T"]],
        "that": [["DH", "AE1", "T"]], "was": [["W", "AA1", "Z"]],
        "for": [["F", "AO1", "R"]], "on": [["AA1", "N"]], "are": [["AA1", "R"]],
        "with": [["W", "IH1", "DH"]], "as": [["AE1", "Z"]], "at": [["AE1", "T"]],
        "be": [["B", "IY1"]], "this": [["DH", "IH1", "S"]], "have": [["HH", "AE1", "V"]],
        "from": [["F", "R", "AH1", "M"]], "or": [["AO1", "R"]], "by": [["B", "AY1"]],
        "not": [["N", "AA1", "T"]], "but": [["B", "AH1", "T"]],
        "what": [["W", "AH1", "T"]], "all": [["AO1", "L"]], "when": [["W", "EH1", "N"]],
        "can": [["K", "AE1", "N"]], "there": [["DH", "EH1", "R"]],
        "their": [["DH", "EH1", "R"]], "will": [["W", "IH1", "L"]],
        "each": [["IY1", "CH"]], "make": [["M", "EY1", "K"]],
        "like": [["L", "AY1", "K"]], "long": [["L", "AO1", "NG"]],
        "just": [["JH", "AH1", "S", "T"]], "over": [["OW1", "V", "ER0"]],
        "such": [["S", "AH1", "CH"]], "good": [["G", "UH1", "D"]],
        "year": [["Y", "IH1", "R"]], "back": [["B", "AE1", "K"]],
        "should": [["SH", "UH1", "D"]], "work": [["W", "ER1", "K"]],
        "people": [["P", "IY1", "P", "AH0", "L"]], "through": [["TH", "R", "UW1"]],
        "she": [["SH", "IY1"]], "would": [["W", "UH1", "D"]], "he": [["HH", "IY1"]],
        "you": [["Y", "UW1"]], "me": [["M", "IY1"]], "we": [["W", "IY1"]],
        "my": [["M", "AY1"]], "your": [["Y", "AO1", "R"]], "up": [["AH1", "P"]],
        "out": [["AW1", "T"]], "day": [["D", "EY1"]], "had": [["HH", "AE1", "D"]],
        "no": [["N", "OW1"]], "way": [["W", "EY1"]], "could": [["K", "UH1", "D"]],
        "house": [["HH", "AW1", "S"]], "about": [["AH0", "B", "AW1", "T"]],
        "old": [["OW1", "L", "D"]], "boy": [["B", "OY1"]], "voice": [["V", "OY1", "S"]],
        "go": [["G", "OW1"]], "fish": [["F", "IH1", "SH"]], "new": [["N", "UW1"]],
        "book": [["B", "UH1", "K"]], "blue": [["B", "L", "UW1"]],
        "judge": [["JH", "AH1", "JH"]], "measure": [["M", "EH1", "ZH", "ER0"]],
        "vision": [["V", "IH1", "ZH", "AH0", "N"]], "sing": [["S", "IH1", "NG"]],
        "morning": [["M", "AO1", "R", "N", "IH0", "NG"]],
        "sun": [["S", "AH1", "N"]], "light": [["L", "AY1", "T"]],
        "kitchen": [["K", "IH1", "CH", "AH0", "N"]], "window": [["W", "IH1", "N", "D", "OW0"]],
        "warm": [["W", "AO1", "R", "M"]], "wood": [["W", "UH1", "D"]],
        "table": [["T", "EY1", "B", "AH0", "L"]], "rain": [["R", "EY1", "N"]],
        "snow": [["S", "N", "OW1"]], "fire": [["F", "AY1", "ER0"]],
        "tree": [["T", "R", "IY1"]], "walk": [["W", "AO1", "K"]],
        "run": [["R", "AH1", "N"]], "thing": [["TH", "IH1", "NG"]],
        "think": [["TH", "IH1", "NG", "K"]], "other": [["AH1", "DH", "ER0"]],
        "father": [["F", "AA1", "DH", "ER0"]], "mother": [["M", "AH1", "DH", "ER0"]],
        "brother": [["B", "R", "AH1", "DH", "ER0"]],
        "street": [["S", "T", "R", "IY1", "T"]],
        "coffee": [["K", "AO1", "F", "IY0"]], "music": [["M", "Y", "UW1", "Z", "IH0", "K"]],
        "church": [["CH", "ER1", "CH"]], "bridge": [["B", "R", "IH1", "JH"]],
        "paper": [["P", "EY1", "P", "ER0"]], "stop": [["S", "T", "AA1", "P"]],
        "baby": [["B", "EY1", "B", "IY0"]], "dog": [["D", "AO1", "G"]],
        "cat": [["K", "AE1", "T"]], "big": [["B", "IH1", "G"]],
        "age": [["EY1", "JH"]], "river": [["R", "IH1", "V", "ER0"]],
        "bath": [["B", "AE1", "TH"]], "zoo": [["Z", "UW1"]],
        "ship": [["SH", "IH1", "P"]], "nation": [["N", "EY1", "SH", "AH0", "N"]],
        "ahead": [["AH0", "HH", "EH1", "D"]], "man": [["M", "AE1", "N"]],
        "come": [["K", "AH1", "M"]], "feel": [["F", "IY1", "L"]],
        "very": [["V", "EH1", "R", "IY0"]], "away": [["AH0", "W", "EY1"]],
        "yes": [["Y", "EH1", "S"]], "cut": [["K", "AH1", "T"]],
        "law": [["L", "AO1"]], "how": [["HH", "AW1"]],
        "time": [["T", "AY1", "M"]], "bed": [["B", "EH1", "D"]],
        "bird": [["B", "ER1", "D"]], "say": [["S", "EY1"]],
        "sit": [["S", "IH1", "T"]], "see": [["S", "IY1"]],
        "home": [["HH", "OW1", "M"]], "join": [["JH", "OY1", "N"]],
        "put": [["P", "UH1", "T"]], "too": [["T", "UW1"]],
        "stream": [["S", "T", "R", "IY1", "M"]], "grabbed": [["G", "R", "AE1", "B", "D"]],
        "slowly": [["S", "L", "OW1", "L", "IY0"]], "toward": [["T", "AH0", "W", "AO1", "R", "D"]],
        "balcony": [["B", "AE1", "L", "K", "AH0", "N", "IY0"]],
        "door": [["D", "AO1", "R"]], "children": [["CH", "IH1", "L", "D", "R", "AH0", "N"]],
        "laughed": [["L", "AE1", "F", "T"]], "played": [["P", "L", "EY1", "D"]],
        "park": [["P", "AA1", "R", "K"]], "across": [["AH0", "K", "R", "AO1", "S"]],
        "building": [["B", "IH1", "L", "D", "IH0", "NG"]],
        "corner": [["K", "AO1", "R", "N", "ER0"]],
        "interesting": [["IH1", "N", "T", "R", "AH0", "S", "T", "IH0", "NG"]],
        "selection": [["S", "AH0", "L", "EH1", "K", "SH", "AH0", "N"]],
        "fresh": [["F", "R", "EH1", "SH"]], "bread": [["B", "R", "EH1", "D"]],
        "bakery": [["B", "EY1", "K", "ER0", "IY0"]],
        "entire": [["EH0", "N", "T", "AY1", "ER0"]],
        "neighborhood": [["N", "EY1", "B", "ER0", "HH", "UH2", "D"]],
    }
    return words


def text_to_phonemes(text: str) -> set[str]:
    """Extract the set of unique phonemes present in a text string.

    Uses the CMU Pronouncing Dictionary to map words to ARPAbet phonemes.
    Stress markers (0, 1, 2) are stripped from vowels.

    Args:
        text: English text string.

    Returns:
        Set of unique ARPAbet phoneme symbols found in the text.
    """
    cmu = _load_cmudict()
    phonemes = set()

    # Normalize and tokenize
    words = re.findall(r"[a-zA-Z']+", text.lower())

    for word in words:
        # Strip possessive/contractions for lookup
        clean_word = word.replace("'", "")
        pronunciations = cmu.get(clean_word, [])

        if pronunciations:
            # Use first pronunciation
            for phone in pronunciations[0]:
                # Strip stress markers (digits) from vowels
                base_phone = re.sub(r"\d", "", phone)
                if base_phone in ALL_PHONEMES:
                    phonemes.add(base_phone)

    return phonemes


def get_coverage_stats(covered_phonemes: set[str]) -> dict:
    """Calculate coverage statistics.

    Args:
        covered_phonemes: Set of phonemes that have been covered.

    Returns:
        Dictionary with overall and per-category coverage stats.
    """
    total = len(ALL_PHONEMES)
    covered = len(covered_phonemes & ALL_PHONEMES)

    category_stats = {}
    for category, phonemes in PHONEME_CATEGORIES.items():
        cat_total = len(phonemes)
        cat_covered = len(set(phonemes) & covered_phonemes)
        category_stats[category] = {
            "total": cat_total,
            "covered": cat_covered,
            "percentage": round(cat_covered / cat_total * 100, 1) if cat_total > 0 else 0,
            "phonemes": {p: p in covered_phonemes for p in phonemes},
        }

    return {
        "total_phonemes": total,
        "covered_phonemes": covered,
        "coverage_percentage": round(covered / total * 100, 1) if total > 0 else 0,
        "missing_phonemes": sorted(ALL_PHONEMES - covered_phonemes),
        "categories": category_stats,
    }


def get_missing_phonemes(covered_phonemes: set[str]) -> list[str]:
    """Get a list of phonemes not yet covered."""
    return sorted(ALL_PHONEMES - covered_phonemes)


def get_phoneme_suggestions_for_prompt(missing: list[str], count: int = 5) -> str:
    """Generate a description of missing phonemes for Claude's prompt generation.

    Args:
        missing: List of missing ARPAbet phonemes.
        count: Number of phonemes to prioritize.

    Returns:
        Human-readable description for Claude's system prompt.
    """
    if not missing:
        return "All phonemes are covered! Generate diverse prompts for quality and variety."

    # Prioritize by category (cover full categories first)
    priority = missing[:count]

    descriptions = []
    for p in priority:
        cat = PHONEME_TO_CATEGORY.get(p, "unknown")
        example_words = _get_example_words(p)
        descriptions.append(f"{p} ({cat}) - e.g., {example_words}")

    return (
        f"Missing {len(missing)} phonemes. Prioritize sentences containing these sounds:\n"
        + "\n".join(f"  - {d}" for d in descriptions)
    )


def _get_example_words(phoneme: str) -> str:
    """Get example words containing a given phoneme."""
    examples = {
        "P": "paper, stop", "B": "baby, job", "T": "take, water", "D": "dog, ladder",
        "K": "cat, back", "G": "go, big", "CH": "church, watch", "JH": "judge, age",
        "F": "fish, enough", "V": "voice, river", "TH": "think, bath",
        "DH": "this, brother", "S": "sun, miss", "Z": "zoo, plays",
        "SH": "ship, nation", "ZH": "measure, vision", "HH": "house, ahead",
        "M": "man, come", "N": "no, sun", "NG": "sing, think",
        "L": "light, feel", "R": "run, very", "W": "we, away", "Y": "yes, you",
        "AA": "father, hot", "AE": "cat, bat", "AH": "cut, but", "AO": "law, caught",
        "AW": "how, about", "AX": "about, sofa", "AY": "my, time",
        "EH": "bed, said", "ER": "bird, her", "EY": "day, say",
        "IH": "sit, him", "IY": "see, me",
        "OW": "go, home", "OY": "boy, join",
        "UH": "book, put", "UW": "too, blue",
    }
    return examples.get(phoneme, "various words")
