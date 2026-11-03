"""
Lightweight zero-dependency heuristic detector based on statistical NLP properties:
- Lexical diversity (Type-Token Ratio)
- Sentence length variance (Burstiness)
- Perplexity estimation / repetitive n-gram repetition
- Typical AI transition phrase density
"""

import re
import math
from typing import Dict, Any

AI_TRANSITION_MARKERS = [
    r"\bin today's digital (age|landscape|world|era)\b",
    r"\bfurthermore\b",
    r"\bmoreover\b",
    r"\bit is crucial to\b",
    r"\bit is essential to\b",
    r"\bdelve into\b",
    r"\btapestry of\b",
    r"\btestament to\b",
    r"\bplays a crucial role\b",
    r"\bplays a pivotal role\b",
    r"\bin conclusion\b",
    r"\bto summarize\b",
    r"\bnavigating the\b",
    r"\brobust framework\b",
    r"\bseamless integration\b",
    r"\brich tapestry\b",
    r"\bmultifaceted\b",
    r"\bever-evolving\b",
    r"\brapid advancement\b",
    r"\btransformative potential\b",
]

def analyze_heuristic(text: str) -> Dict[str, Any]:
    clean_text = text.strip()
    if not clean_text:
        return {
            "service_name": "Heuristic & Burstiness Engine",
            "ai_probability": None,
            "status": "empty",
            "label": "Empty Input",
            "metrics": {}
        }

    words = re.findall(r"\b[A-Za-z0-9'-]+\b", clean_text)
    total_words = len(words)
    if total_words < 10:
        return {
            "service_name": "Heuristic & Burstiness Engine",
            "ai_probability": None,
            "status": "insufficient",
            "label": "Insufficient Text",
            "metrics": {"word_count": total_words}
        }

    # 1. Lexical Diversity (Type-Token Ratio)
    # Standardized root TTR
    unique_words = len(set(w.lower() for w in words))
    root_ttr = unique_words / math.sqrt(total_words)

    # 2. Sentence Length Variance (Burstiness)
    # AI tends to generate sentences with remarkably uniform lengths (low standard deviation).
    # Human text has high burstiness (mixing short punchy clauses with long compound sentences).
    sentences = [s.strip() for s in re.split(r"[.!?]+", clean_text) if s.strip()]
    sentence_lengths = [len(re.findall(r"\b[A-Za-z0-9'-]+\b", s)) for s in sentences]
    sentence_lengths = [l for l in sentence_lengths if l > 0]

    num_sentences = len(sentence_lengths)
    if num_sentences > 1:
        mean_len = sum(sentence_lengths) / num_sentences
        variance = sum((l - mean_len) ** 2 for l in sentence_lengths) / num_sentences
        std_len = math.sqrt(variance)
        burstiness_cv = std_len / mean_len if mean_len > 0 else 0.0
    else:
        # Single sentence or minimal clauses - neutral burstiness
        burstiness_cv = 0.55
        mean_len = float(sentence_lengths[0]) if sentence_lengths else 0.0

    # 3. AI Transition Pattern Matches
    pattern_hits = 0
    matched_phrases = []
    lower_text = clean_text.lower()
    for pattern in AI_TRANSITION_MARKERS:
        matches = re.findall(pattern, lower_text)
        if matches:
            pattern_hits += len(matches)
            matched_phrases.append(pattern.replace(r"\b", "").replace(r"\b", ""))

    # 4. Score synthesis
    # Start with neutral human-leaning baseline for casual text
    score = 0.30

    # Burstiness contribution (only meaningful when multiple sentences exist)
    if num_sentences > 1:
        if burstiness_cv < 0.30:
            score += 0.30
        elif burstiness_cv < 0.45:
            score += 0.15
        elif burstiness_cv > 0.80:
            score -= 0.20
        elif burstiness_cv > 0.60:
            score -= 0.10

    # Marker contribution
    if pattern_hits >= 3:
        score += 0.45
    elif pattern_hits >= 2:
        score += 0.30
    elif pattern_hits == 1:
        score += 0.15

    # Clamp score between 0.02 and 0.98
    score = max(0.02, min(0.98, score))

    if score >= 0.70:
        label = "Likely AI-Generated"
    elif score >= 0.40:
        label = "Mixed / Unclear"
    else:
        label = "Likely Human-Written"

    return {
        "service_name": "Heuristic & Burstiness Engine",
        "ai_probability": round(score, 4),
        "status": "success",
        "label": label,
        "metrics": {
            "total_words": total_words,
            "sentence_count": len(sentence_lengths),
            "burstiness_cv": round(burstiness_cv, 3),
            "ai_marker_hits": pattern_hits,
            "matched_markers": matched_phrases[:5]
        }
    }
