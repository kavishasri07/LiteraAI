
import requests
from app.core.config import settings


def generate_answer(question: str, evidence: list[dict]) -> str | None:

    if not settings.ollama_enabled:
        print("Ollama is disabled in configuration.")
        return None

    if not evidence:
        return None

    context = "\n\n".join(
        f"[{i}] Paper: {e['title']} | Page: {e['page_number']}\n"
        f"Evidence: {e['content']}"
        for i, e in enumerate(evidence, start=1)
    )

    prompt = f"""
You are LiteraAI, an academic research assistant.

Your task is to answer the user's question using ONLY the
provided research paper evidence.

STRICT RULES:
1. Do not invent facts or information.
2. Do not use outside knowledge.
3. Explain the answer clearly in simple academic language.
4. Organize the answer using headings and numbered steps
   whenever appropriate.
5. Cite the actual paper page number for every important claim.
6. Use citations in this format: (Page 3).
7. If evidence is insufficient, clearly mention what is missing.
8. Do not simply copy and paste the retrieved passages.
9. Combine related evidence into a coherent explanation.
10. Never claim something that the evidence does not support.

USER QUESTION:
{question}

RETRIEVED PAPER EVIDENCE:
{context}

Write a well-structured, evidence-grounded answer.

ANSWER:
"""

    try:
        print(f"Sending question to Ollama model: {settings.ollama_model}")

        response = requests.post(
            f"{settings.ollama_base_url.rstrip('/')}/api/generate",
            json={
                "model": settings.ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2
                }
            },
            timeout=settings.ollama_timeout_seconds,
        )

        response.raise_for_status()

        data = response.json()
        answer = data.get("response", "").strip()

        if not answer:
            print("Ollama returned an empty response.")
            return None

        print("Ollama successfully generated an answer.")
        return answer

    except requests.RequestException as exc:
        print(f"Ollama connection/request error: {exc}")
        return None

    except (ValueError, KeyError) as exc:
        print(f"Invalid Ollama response: {exc}")
        return None
