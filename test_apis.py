# test_apis.py
import os
from dotenv import load_dotenv
from openai import OpenAI
from anthropic import Anthropic
import requests

# Load environment variables
load_dotenv()

# Test OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hi"}]
)
print("OpenAI works:", response.choices[0].message.content[:50])

# Test Claude
claude = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
message = claude.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=100,
    messages=[{"role": "user", "content": "Hi"}]
)
print("Claude works:", message.content[0].text[:50])

# Test Exa
exa_response = requests.post(
    "https://api.exa.ai/search",
    headers={"x-api-key": os.getenv("EXA_API_KEY")},
    json={"query": "design patterns", "numResults": 2}
)
print("Exa works:", exa_response.status_code == 200)

# Test Brave
brave_response = requests.get(
    "https://api.search.brave.com/res/v1/web/search",
    headers={"X-Subscription-Token": os.getenv("BRAVE_API_KEY")},
    params={"q": "test", "count": 2}
)
print("Brave works:", brave_response.status_code == 200)

# Test Jina (free endpoint)
jina_response = requests.get("https://r.jina.ai/https://example.com")
print("Jina works:", jina_response.status_code == 200)