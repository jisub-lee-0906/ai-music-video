def enforce_t5_length(text: str, max_tokens: int = 120) -> str:
    words = text.split()
    return " ".join(words[:max_tokens])

