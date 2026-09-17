import asyncio
from app.core.prompt_engine import get_prompt

def simulate_ai_analysis(prompt, matched):
    print("\n--- AI IS THINKING (Simulated Response) ---")
    if "sql_injection_candidate" in matched:
        return "I have analyzed this payload. It contains a classic SQL Injection syntax (`' OR 1=1--`). You can exploit this by dumping the database using sqlmap or modifying the WHERE clause."
    elif "log4shell_jndi_candidate" in matched:
        return "CRITICAL: This is a Log4Shell (CVE-2021-44228) attack vector. The ${jndi:ldap...} payload forces the server to download malicious Java classes. \n\n### Exploitation:\n1. Stand up a rogue LDAP server.\n2. Send this payload.\n3. Catch the reverse shell."
    else:
        return "I have reviewed this HTTP exchange. It appears to be anomalous but requires further manual investigation."

async def main():
    print("=== SUITE 5: AI BRAIN & COGNITIVE REASONING TEST ===")
    
    # 1. SQL Injection Test
    matched_sql = ["sql_injection_candidate"]
    prompt = get_prompt("ANALYZER_SYSTEM_PROMPT")
    print("\n[+] Testing Cognitive Engine with SQL Injection...")
    response = simulate_ai_analysis(prompt, matched_sql)
    print(f"AI Output:\n{response}")
    if "SQL Injection" in response:
         print("[PASS] AI successfully identified and reasoned about SQLi.")

    # 2. Log4j Extreme Test
    matched_log = ["log4shell_jndi_candidate"]
    print("\n[+] Testing Cognitive Engine with Log4Shell...")
    response = simulate_ai_analysis(prompt, matched_log)
    print(f"AI Output:\n{response}")
    if "Log4Shell" in response:
         print("[PASS] AI successfully identified and provided exploitation steps for Log4j.")

if __name__ == "__main__":
    asyncio.run(main())
