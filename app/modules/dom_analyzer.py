import re
from bs4 import BeautifulSoup
import logging
import asyncio

logger = logging.getLogger("burpnake.dom")

class DOMAnalyzer:
    def __init__(self):
        # API endpoints, JWTs, keys in inline scripts
        self.api_pattern = re.compile(r'[''"](/[a-zA-Z0-9_./-]*api[a-zA-Z0-9_./-]*)[''"]')
        
    async def analyze_async(self, html_content: str) -> dict:
        """Asenkron DOM analizi (event loop kilitlememesi icin)."""
        return await asyncio.to_thread(self.analyze, html_content)
        
    def analyze(self, html_content: str) -> dict:
        result = {
            "hidden_inputs": [],
            "forms": [],
            "comments": [],
            "api_endpoints": [],
            "scripts_count": 0
        }
        
        if not html_content:
            return result
            
        try:
            # lxml parser is fast and lenient
            soup = BeautifulSoup(html_content, 'lxml')
            
            # 1. Hidden Inputs (CSRF, State, IDOR targets)
            for hidden in soup.find_all('input', type='hidden'):
                name = hidden.get('name', 'unknown')
                val = hidden.get('value', '')
                result["hidden_inputs"].append({"name": name, "value": val[:100]})
                
            # 2. Forms structure (to know what parameters are accepted)
            for form in soup.find_all('form'):
                action = form.get('action', '')
                method = form.get('method', 'GET').upper()
                inputs = [inp.get('name') for inp in form.find_all('input') if inp.get('name')]
                result["forms"].append({"action": action, "method": method, "inputs": inputs})
                
            # 3. HTML Comments (developer notes, endpoints)
            from bs4 import Comment
            for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
                c_text = comment.strip()
                if c_text and len(c_text) < 500:
                    result["comments"].append(c_text)
                    
            # 4. Inline Scripts / API Endpoints
            scripts = soup.find_all('script')
            result["scripts_count"] = len(scripts)
            
            for script in scripts:
                if script.string:
                    # Search for API endpoints in string
                    matches = self.api_pattern.findall(script.string)
                    result["api_endpoints"].extend(matches)
                    
            result["api_endpoints"] = list(set(result["api_endpoints"]))
            
        except Exception as e:
            logger.error(f"[DOM] Parsing error: {e}")
            
        return result

dom_analyzer = DOMAnalyzer()