import re
from collections import Counter
from app.database.db import db_session

STOPWORDS = {"the","a","an","and","or","of","to","in","on","for","is","are","was","were","with","by","from","what","how","which","does","this","that","paper","research"}

def terms(text):
    return [t for t in re.findall(r"[a-zA-Z0-9][a-zA-Z0-9_-]+", text.lower()) if t not in STOPWORDS]

def retrieve(question: str, paper_ids=None, limit=6):
    q_terms = terms(question)
    if not q_terms:
        return []
    with db_session() as conn:
        params = []
        where = ""
        if paper_ids:
            marks = ",".join("?" for _ in paper_ids)
            where = f" AND c.paper_id IN ({marks})"
            params.extend(paper_ids)
        rows = conn.execute(
            "SELECT c.id,c.paper_id,c.page_number,c.section,c.content,p.title FROM chunks c JOIN papers p ON p.id=c.paper_id WHERE 1=1" + where,
            params
        ).fetchall()
    scored = []
    qset = set(q_terms)
    for row in rows:
        frequencies = Counter(terms(row["content"]))
        if not frequencies:
            continue
        counts = sum(frequencies[t] for t in qset)
        coverage = len(qset.intersection(frequencies)) / max(1, len(qset))
        score = counts / (sum(frequencies.values()) ** 0.45) + coverage
        if score > 0:
            scored.append((score, dict(row)))
    scored.sort(key=lambda item: item[0], reverse=True)
    results = []
    for score, item in scored[:limit]:
        item["score"] = round(score, 4)
        results.append(item)
    return results
