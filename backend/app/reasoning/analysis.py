import re
from collections import Counter

GAP_TERMS = ("limitation", "future work", "future research", "however", "challenge", "not address", "small dataset", "lack of")

def compare_papers(papers, chunks_by_paper):
    output = []
    dimensions = {
        "Objective / abstract": ("abstract", "objective", "aim", "purpose"),
        "Methodology": ("method", "approach", "proposed", "architecture"),
        "Dataset": ("dataset", "data set", "corpus"),
        "Evaluation": ("accuracy", "precision", "recall", "f1", "rmse", "mae", "evaluation"),
        "Limitations": ("limitation", "future work", "challenge", "constraint"),
    }
    for paper in papers:
        text = "\n".join(c["content"] for c in chunks_by_paper.get(paper["id"], []))
        lower = text.lower()
        fields = {}
        for label, needles in dimensions.items():
            snippets = []
            for sentence in re.split(r"(?<=[.!?])\s+", text):
                if any(n in sentence.lower() for n in needles) and len(sentence.strip()) > 30:
                    snippets.append(sentence.strip()[:420])
                if len(snippets) == 2:
                    break
            fields[label] = " ".join(snippets) if snippets else "Not clearly extracted in this MVP."
        output.append({"paper_id": paper["id"], "title": paper["title"], "fields": fields})
    return output

def research_gaps(papers, chunks_by_paper):
    candidates = []
    for paper in papers:
        for chunk in chunks_by_paper.get(paper["id"], []):
            low = chunk["content"].lower()
            if any(term in low for term in GAP_TERMS):
                candidates.append({
                    "paper_id": paper["id"], "paper_title": paper["title"],
                    "page_number": chunk["page_number"],
                    "evidence": chunk["content"][:500],
                    "suggestion": "Review this stated limitation and test whether it recurs across the selected corpus."
                })
    return candidates[:30]

def build_graph(papers, chunks_by_paper):
    nodes, edges = [], []
    topic_map = {}
    for paper in papers:
        nodes.append({"id": paper["id"], "label": paper["title"][:42], "type": "paper"})
        text = " ".join(c["content"] for c in chunks_by_paper.get(paper["id"], [])).lower()
        terms = ["transformer", "convolutional neural network", "cnn", "random forest", "svm", "deep learning", "machine learning", "benchmark", "dataset"]
        for term in terms:
            if term in text:
                tid = "topic:" + term
                if tid not in topic_map:
                    topic_map[tid] = {"id": tid, "label": term, "type": "topic"}
                edges.append({"source": paper["id"], "target": tid, "label": "MENTIONS"})
    nodes.extend(topic_map.values())
    return {"nodes": nodes, "edges": edges}
