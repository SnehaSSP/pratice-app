import os
import re
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic

# ---------- Setup ----------
load_dotenv(override=True)
client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip())
MODEL = "claude-sonnet-5-5"
DOC_PATH = Path(__file__).parent.parent / "docs" / "requirements.md"


# ---------- 1. Load the document and split it into chunks ----------
def load_chunks(path):
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"\n(?=## )", text)              # split before every "## " heading
    return [p.strip() for p in parts if p.strip().startswith("## ")]


CHUNKS = load_chunks(DOC_PATH)
print(f"📚 Loaded {len(CHUNKS)} chunks from {DOC_PATH.name}")


# ---------- 2. RETRIEVE: simple keyword search ----------
STOP_WORDS = {"the", "and", "for", "are", "what", "which", "how", "does", "must",
              "with", "that", "this", "when", "can", "user", "users", "is", "a"}

def words(text):
    return {w for w in re.findall(r"[a-z0-9]+", text.lower())
            if len(w) > 2 and w not in STOP_WORDS}


def search(question, top_k=3):
    q_words = words(question)
    scored = []
    for chunk in CHUNKS:
        score = len(q_words & words(chunk))           # how many words they share
        scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [(score, chunk) for score, chunk in scored[:top_k] if score > 0]


# ---------- 3. AUGMENT + GENERATE ----------
def ask(question):
    results = search(question)

    print("\n🔎 Retrieved chunks:")
    if not results:
        print("   (nothing matched)")
    for score, chunk in results:
        print(f"   score={score} → {chunk.splitlines()[0]}")

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
    print("\n💬 Claude:", response.content[0].text)


# ---------- 4. Ask questions ----------
while True:
    q = input("\n❓ Ask about the requirements (or 'quit'): ").strip()
    if q.lower() in ("quit", "exit", ""):
        break
    ask(q)
