import os
from dotenv import load_dotenv
load_dotenv(override=True)          # .env wins over any old key in your shell
from anthropic import Anthropic

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip())


response = client.messages.create(model="claude-sonnet-5-5",
                              max_tokens = 500, system="You are a friendly QA mentor. Keep answers short and simple.",
                              messages=[
                                  {"role": "user", "content": "What is Playwright, in 3 lines?"}
                              ],
                              )

print("Claude says:\n", response.content[0].text)
print("\n--- details ---")
print("Stop reason:", response.stop_reason)
print("Input tokens:", response.usage.input_tokens)
print("Output tokens:", response.usage.output_tokens)

