from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")

texts = [
    "Which jobs can a person have?",
    "Allowed roles are QA Engineer, Developer and Manager.",
    "How do I remove someone from the list?",
    "Clicking Delete removes that user from the table.",
    "What is the office wifi password?",
]

vectors = model.encode(texts, normalize_embeddings=True)
print("Each text becomes", len(vectors[0]), "numbers. First 5 of text 1:", vectors[0][:5])

print("\nSimilarity (closer to 1 = more similar meaning):")
print(f"jobs  vs roles   : {vectors[0] @ vectors[1]:.2f}")
print(f"remove vs Delete : {vectors[2] @ vectors[3]:.2f}")
print(f"jobs  vs wifi    : {vectors[0] @ vectors[4]:.2f}")
