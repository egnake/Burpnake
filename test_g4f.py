import asyncio
from g4f.client import Client

async def main():
    client = Client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "hello"}],
    )
    print(response.choices[0].message.content)

if __name__ == "__main__":
    asyncio.run(main())
