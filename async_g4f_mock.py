import asyncio
from g4f.client import AsyncClient

async def main():
    client = AsyncClient()
    prompt = """Perform a deep security analysis of this HTTP exchange.

REQUEST:
POST /api/v2/document/export HTTP/1.1
Host: api.target.com
Content-Type: application/json
Authorization: Bearer eyJ...

{
  "doc_id": "789",
  "format": "pdf",
  "options": {
    "margin": "1cm",
    "headerTemplate": "<h1>Draft</h1>"
  }
}

RESPONSE:
HTTP/1.1 500 Internal Server Error
Content-Type: application/json

{
  "error": "Generation failed",
  "details": "Error: Failed to launch chrome!\n[1105/103412.123:ERROR:zygote_host_impl_linux.cc(90)] Running as root without --no-sandbox is not supported."
}

Provide:
1. Deep Chain-of-Thought (CoT) Analysis: Walk through your thought process. What does the response body tell you? Did you get an error? What does the status code imply? For example, "I see the response body reflects our input, but the angle brackets are HTML-encoded, so XSS is unlikely here. However, wait, in the JSON response, the input is unescaped..."
2. Identified vulnerabilities or suspicious patterns based on your analysis
3. Specific parameters to test
4. Exact payloads to try (Provide Plan A, Plan B, and Plan C)
5. Actionable Next Steps:
   - Provide the exact `curl` command.
   - If dynamic modification is needed, provide Burp Suite Match and Replace rules.
   - If automation is needed (e.g. race condition, fuzzing), provide a short Python `requests` script.
6. Expected behavior if vulnerable
7. Impact assessment
"""
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a senior bug bounty hunter."},
                {"role": "user", "content": prompt}
            ]
        )
        print(response.choices[0].message.content)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
