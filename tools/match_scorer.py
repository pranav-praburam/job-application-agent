import re

_STOP = {
    "and", "the", "for", "with", "that", "this", "are", "you", "our", "your",
    "will", "have", "from", "not", "but", "has", "been", "they", "their", "can",
    "into", "also", "all", "any", "both", "each", "more", "most", "other",
    "some", "such", "than", "then", "these", "those", "when", "which", "who",
    "why", "how", "what", "where", "its", "use", "used", "using", "work",
    "able", "about", "after", "against", "along", "across", "an", "as", "at",
    "be", "between", "by", "do", "during", "few", "in", "is", "it", "of",
    "on", "or", "to", "up", "we", "were", "while", "a", "an", "the",
    "experience", "role", "team", "help", "strong", "working", "including",
    "looking", "great", "great", "new", "good", "well", "must",
}


def _terms(text: str) -> set[str]:
    """Lowercase alphanumeric tokens ≥3 chars, excluding stop words."""
    tokens = re.findall(r"[a-z][a-z0-9+#.\-]{2,}", text.lower())
    return {t for t in tokens if t not in _STOP}


def score_match(job_description: str, resume_text: str) -> float:
    """
    Return 0-100 score: fraction of the job description's meaningful terms
    that also appear in the resume, scaled so a strong match reads ~70-90.
    """
    if not job_description or not resume_text:
        return 0.0
    job_terms = _terms(job_description)
    resume_terms = _terms(resume_text)
    if not job_terms:
        return 0.0
    overlap = job_terms & resume_terms
    raw = len(overlap) / len(job_terms)  # 0-1, fraction of job terms covered
    scaled = round(min(raw * 140, 100), 1)
    return scaled
