"""
NEU Unofficial Guide — Gradio Interface (Milestone 5)

Run:    python app.py
Opens a local web UI at http://127.0.0.1:7860

End-to-end flow:
    user question  →  retrieve top-5 chunks from ChromaDB
                  →  Groq (llama-3.3-70b-versatile) answers using ONLY those chunks
                  →  answer shown with cited source filenames
                  →  if no chunk clears the relevance floor, the app refuses to answer
"""

import gradio as gr

from pipeline import (
    load_documents,
    chunk_text,
    embed_and_store,
    generate_answer,
    TOP_K,
)

# ---------------------------------------------------------------------------
# One-time pipeline setup at startup — load docs, chunk, embed, open collection.
# ---------------------------------------------------------------------------
print("Initializing NEU Unofficial Guide pipeline …")
_docs   = load_documents()
_chunks = chunk_text(_docs)
COLLECTION = embed_and_store(_chunks)
print(f"Ready — {COLLECTION.count()} chunks indexed.\n")


# ---------------------------------------------------------------------------
# Handler — what the UI calls when the user submits a question
# ---------------------------------------------------------------------------
def handle_query(question: str):
    if not question or not question.strip():
        return "Please enter a question.", "", ""

    result = generate_answer(question, COLLECTION)

    answer = result["answer"]

    if result["sources"]:
        sources = "\n".join(f"• {s}" for s in result["sources"])
    else:
        sources = "(no relevant sources found — see refusal message above)"

    # Show retrieved chunks for transparency
    chunks_view = "\n\n".join(
        f"[Rank {c['rank']}] similarity={c['score']}  source={c['source']}\n"
        f"{c['text'][:400]}{'…' if len(c['text']) > 400 else ''}"
        for c in result["chunks"]
    ) or "(no chunks retrieved)"

    return answer, sources, chunks_view


# ---------------------------------------------------------------------------
# UI layout
# ---------------------------------------------------------------------------
SAMPLE_QUESTIONS = [
    "What do students say about the workload in CS 3500?",
    "Which professor gives strong exam reviews?",
    "Is Northeastern's CS program good for co-op outcomes?",
    "How hard is it to get good grades in NEU's CS master's courses?",
    "What is Karl Lieberherr's reputation among CS students?",
    "What is the best dining hall on campus?",  # tests refusal — corpus has no dining info
]

with gr.Blocks(title="NEU Unofficial Guide", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        """
        # 🎓 NEU Unofficial Guide
        Ask about Northeastern CS professors, courses, workload, and co-op outcomes.
        Answers are grounded in real student reviews — the system will refuse if its sources don't cover your question.
        """
    )

    with gr.Row():
        question_box = gr.Textbox(
            label="Your question",
            placeholder="e.g. What do students say about Benjamin Lerner?",
            lines=2,
            scale=4,
        )
        ask_btn = gr.Button("Ask", variant="primary", scale=1)

    gr.Examples(
        examples=[[q] for q in SAMPLE_QUESTIONS],
        inputs=question_box,
        label="Try one of these",
    )

    answer_box = gr.Textbox(label="Answer", lines=6, interactive=False)
    sources_box = gr.Textbox(label="Sources cited", lines=4, interactive=False)

    with gr.Accordion("🔎 Retrieved chunks (top-5)", open=False):
        chunks_box = gr.Textbox(label="", lines=20, interactive=False, show_label=False)

    ask_btn.click(
        handle_query,
        inputs=question_box,
        outputs=[answer_box, sources_box, chunks_box],
    )
    question_box.submit(
        handle_query,
        inputs=question_box,
        outputs=[answer_box, sources_box, chunks_box],
    )


if __name__ == "__main__":
    demo.launch()
