import re

from app.retrieval.retriever import terms


def extractive_answer(question: str, evidence: list[dict]) -> str:
    """Return only retrieved sentences that overlap the question's key terms."""
    query_terms = set(terms(question))
    if not query_terms:
        return f"I couldn't identify searchable terms in “{question}”. Try including a method, dataset, result, or limitation from the paper."

    matches = []
    for citation_id, item in enumerate(evidence, start=1):
        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+|\n+", item["content"])
            if sentence.strip()
        ]
        for sentence in sentences:
            sentence_terms = set(terms(sentence))
            overlap = query_terms.intersection(sentence_terms)
            if not overlap:
                continue
            coverage = len(overlap) / len(query_terms)
            score = len(overlap) + coverage + item.get("score", 0) * 0.05
            matches.append((score, citation_id, item, sentence))

    if not matches:
        return f"I couldn't find a passage that directly addresses “{question}” in the uploaded papers. Try using terms that appear in the paper."

    matches.sort(key=lambda match: match[0], reverse=True)
    selected = []
    seen = set()
    for _, citation_id, item, sentence in matches:
        key = (citation_id, sentence)
        if key in seen:
            continue
        seen.add(key)
        selected.append((citation_id, item, sentence))
        if len(selected) == 3:
            break

    excerpts = "\n\n".join(
        f"[{citation_id}] {item['title']} (page {item['page_number']}): “{sentence}”"
        for citation_id, item, sentence in selected
    )
    return f"For “{question}”, these retrieved sentences have the closest matching terms. They are evidence excerpts, not a synthesized or semantically verified answer:\n\n{excerpts}"
