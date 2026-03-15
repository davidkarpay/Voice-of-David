"""Anthropic API service for generating recording prompts.

Uses Claude to generate varied, natural-sounding text prompts
targeted at specific phoneme coverage gaps and recording categories.
"""

import anthropic
from typing import Optional
from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL


SYSTEM_PROMPT = """You are a voice recording prompt generator for a text-to-speech (TTS) voice
cloning dataset. Your job is to create natural, varied sentences that a person
will read aloud to record their voice.

RULES:
1. Each sentence should be 8-25 words long (roughly 3-15 seconds when spoken naturally).
2. Sentences must sound natural when read aloud -- no awkward constructions.
3. Avoid tongue twisters, unusual names, or words that are hard to pronounce.
4. Vary sentence structure: declarative, interrogative, imperative, exclamatory.
5. Vary emotional tone: neutral, warm, serious, curious, enthusiastic.
6. Do not repeat themes or sentence patterns within a batch.
7. Return ONLY the sentences, one per line, with no numbering or formatting.

CATEGORIES:
- phonetic: Sentences targeting specific phoneme sounds. Focus on natural sentences
  that happen to contain the target sounds frequently.
- conversational: Casual speech patterns, the way someone talks to a friend or colleague.
- emotional: Sentences that naturally evoke different emotional deliveries.
- domain: Professional/technical sentences from a specific field.
- narrative: Storytelling sentences with varied rhythm and pacing.
"""


async def generate_prompts(
    category: str,
    count: int = 10,
    phoneme_guidance: Optional[str] = None,
    existing_texts: Optional[list[str]] = None,
) -> list[str]:
    """Generate recording prompts using Claude.

    Args:
        category: One of phonetic, conversational, emotional, domain, narrative.
        count: Number of prompts to generate.
        phoneme_guidance: Description of missing phonemes to target.
        existing_texts: List of already-recorded texts to avoid repetition.

    Returns:
        List of generated prompt strings.
    """
    if not ANTHROPIC_API_KEY:
        raise ValueError(
            "ANTHROPIC_API_KEY environment variable is not set. "
            "Set it to your Anthropic API key to enable prompt generation."
        )

    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    user_message = f"Generate {count} {category} recording prompts."

    if phoneme_guidance:
        user_message += f"\n\nPhoneme targeting:\n{phoneme_guidance}"

    if existing_texts and len(existing_texts) > 0:
        # Send a sample of existing texts to avoid repetition
        sample = existing_texts[-20:] if len(existing_texts) > 20 else existing_texts
        user_message += "\n\nAvoid repeating themes from these already-recorded sentences:\n"
        user_message += "\n".join(f"- {t}" for t in sample)

    if category == "domain":
        user_message += (
            "\n\nDomain: Criminal defense law. Include sentences about courtroom proceedings, "
            "client advocacy, legal arguments, procedural matters, and interactions with "
            "judges, prosecutors, and witnesses. Keep them natural -- the way a lawyer "
            "actually speaks, not how legal textbooks read."
        )

    response = await client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    # Parse response into individual sentences
    text = response.content[0].text
    sentences = [line.strip() for line in text.strip().split("\n") if line.strip()]

    # Filter out any numbering artifacts
    cleaned = []
    for s in sentences:
        # Remove leading numbers like "1.", "1)", "- "
        import re
        s = re.sub(r"^\d+[\.\)]\s*", "", s)
        s = re.sub(r"^[-*]\s*", "", s)
        s = s.strip()
        if s and len(s) > 10:
            cleaned.append(s)

    return cleaned[:count]


async def generate_prompts_fallback(
    category: str,
    count: int = 10,
) -> list[str]:
    """Generate prompts without the Anthropic API using built-in templates.

    Used as a fallback when the API key is not configured.
    """
    templates = {
        "phonetic": [
            "The morning sunlight warmed the kitchen as she poured her coffee.",
            "Please pass the butter and the fresh bread from the bakery.",
            "We should leave early to avoid the traffic on the highway.",
            "The children played quietly in the garden behind the house.",
            "Several birds perched on the telephone wire outside my window.",
            "The weather forecast predicted rain for the rest of the week.",
            "She carefully arranged the flowers in a tall glass vase.",
            "The musician tuned his guitar before the evening performance.",
            "Fresh vegetables from the market make the best homemade soup.",
            "The old bridge over the river has stood for a hundred years.",
        ],
        "conversational": [
            "Hey, did you catch the game last night? It was pretty intense.",
            "I was thinking we could grab lunch somewhere downtown today.",
            "So what ended up happening with that project you were working on?",
            "Honestly, I think the first option makes the most sense here.",
            "Yeah, that sounds good to me. Let me check my schedule real quick.",
            "You know what, I completely forgot about that. Thanks for reminding me.",
            "I mean, it could work, but I have a few concerns about the timeline.",
            "Wait, are you serious? When did that happen?",
            "No worries at all. These things take time to figure out.",
            "Let me think about it and get back to you by tomorrow morning.",
        ],
        "emotional": [
            "I cannot believe they actually made it happen after all these years.",
            "This is exactly what we needed. Everything is going to be fine.",
            "I am so disappointed that we missed the deadline by just one day.",
            "That was the most incredible performance I have ever witnessed.",
            "Please be careful out there. The roads are extremely dangerous tonight.",
            "I want to sincerely thank everyone who helped make this possible.",
            "The news hit harder than I expected. I needed a moment to process it.",
            "We did it! Against all odds, we actually pulled it off!",
            "I understand your frustration, and I promise we will find a solution.",
            "Sometimes the quiet moments are the ones that matter the most.",
        ],
        "domain": [
            "Your Honor, the defense requests a continuance to review the new evidence.",
            "My client has no prior record and poses no flight risk to this community.",
            "The prosecution has failed to establish probable cause for the search.",
            "We need to discuss the plea agreement before the hearing tomorrow morning.",
            "The witness testimony contradicts the physical evidence presented by the state.",
            "I would like to note for the record that my client invokes his right to remain silent.",
            "The arresting officer did not read Miranda rights at the time of detention.",
            "We are prepared to present three character witnesses on behalf of the defendant.",
            "The state's evidence is entirely circumstantial and insufficient for conviction.",
            "Can we schedule a sidebar to discuss a matter outside the presence of the jury?",
        ],
        "narrative": [
            "The door creaked open slowly, revealing a room no one had entered in years.",
            "She set down her bag, took a deep breath, and stepped into the unfamiliar office.",
            "By the time they reached the summit, the sun was already beginning to set.",
            "The letter arrived on a Tuesday, and nothing was quite the same after that.",
            "He paused at the corner, unsure which direction would take him home.",
            "Three generations of the family had gathered under one roof for the first time.",
            "The rain stopped as suddenly as it had started, leaving the streets glistening.",
            "She opened the old book carefully, and a photograph slipped from between the pages.",
            "The city looked different at night, alive with sounds and shadows.",
            "It was the kind of morning that made you want to start everything over.",
        ],
    }

    prompts = templates.get(category, templates["phonetic"])
    return prompts[:count]
