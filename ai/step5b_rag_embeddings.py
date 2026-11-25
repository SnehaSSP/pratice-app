import os
os.environ["HF_HUB_OFFLINE"] = "1"              # use the cached model, don't contact Hugging Face
os.environ["TRANSFORMERS_VERBOSITY"] = "error"   # hide info messages

import re
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from anthropic import Anthropic
from sentence_transformers import SentenceTransformer

# ---------- Setup ----------
load_dotenv(override=True)
client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip())
MODEL = "claude-sonnet-5-5"
DOC_PATH = Path(__file__).parent.parent / "docs" / "requirements.md"
MIN_SCORE = 0.25      # ignore chunks that are not similar enough


# ---------- 1. Load the document and split it into chunks ----------
def load_chunks(path):
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"\n(?=## )", text)              # split before every "## " heading
    return [p.strip() for p in parts if p.strip().startswith("## ")]


CHUNKS = load_chunks(DOC_PATH)


# ---------- 2. Embed every chunk once, at startup ----------
print("🧠 Loading embedding model...")
embedder = SentenceTransformer("all-MiniLM-L6-v2")
CHUNK_VECTORS = embedder.encode(CHUNKS, normalize_embeddings=True)   # shape: (12, 384)
print(f"📚 Embedded {len(CHUNKS)} chunks from {DOC_PATH.name}")


# ---------- 3. RETRIEVE: search by meaning ----------
def search(question, top_k=3):
    q_vector = embedder.encode(question, normalize_embeddings=True)   # shape: (384,)
    scores = CHUNK_VECTORS @ q_vector             # cosine similarity with every chunk
    best = np.argsort(scores)[::-1][:top_k]       # indexes of the highest scores
    return [(float(scores[i]), CHUNKS[i]) for i in best if scores[i] >= MIN_SCORE]


# ---------- 4. AUGMENT + GENERATE ----------
def ask(question):
    results = search(question)

    print("\n🔎 Retrieved chunks:")
    if not results:
        print("   (nothing similar enough)")
    for score, chunk in results:
        print(f"   score={score:.2f} → {chunk.splitlines()[0]}")

    context = "\n\n---\n\n".join(chunk for _, chunk in results)

    prompt = f"""Answer the question using ONLY the requirements below.
Always mention the requirement ID (like R3).
If the answer is not in the requirements, say exactly: "Not in the requirements."

<requirements>
{context}
</requirements>

Question: {question}"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    answer = "".join(block.text for block in response.content if block.type == "text")
    print("\n💬 Claude:", answer)


# ---------- 5. Ask questions ----------
while True:
    q = input("\n❓ Ask about the requirements (or 'quit'): ").strip()
    if q.lower() in ("quit", "exit", ""):
        break
    ask(q)
