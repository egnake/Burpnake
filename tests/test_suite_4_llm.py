import asyncio
import os

os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
os.environ["GEMINI_API_KEY"] = "fake_key_for_testing"

from app.core.llm_gateway import llm_gateway

async def main():
    print("=== SUITE 4: LLM GATEWAY CHAOS TEST ===")
    
    print("Attempting to send prompt to LLM Gateway...")
    
    try:
        response = await llm_gateway.generate("hello", prefer="g4f")
        print(f"[PASS] LLM returned data: {response[:100]}...")
    except Exception as e:
        print(f"[EXPECTED FAIL] The Gateway correctly raised an error when all providers failed.")
        print(f"Error caught: {type(e).__name__} - {e}")
        
    print("\nChecking Provider Status...")
    status = await llm_gateway.check_providers()
    print(f"Provider Status: {status}")

if __name__ == "__main__":
    asyncio.run(main())
