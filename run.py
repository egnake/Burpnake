#!/usr/bin/env python3
"""BurpNake - AI-Powered Bug Bounty Hunting Platform"""

import uvicorn
from app.config import settings

def main():
    print(r"""
    ____                   _   __      __        
   / __ )__  ___________  / | / /___ _/ /_____  
  / __  / / / / ___/ __ \/  |/ / __ `/ //_/ _ \ 
 / /_/ / /_/ / /  / /_/ / /|  / /_/ / ,< /  __/ 
/_____/\__,_/_/  / .___/_/ |_/\__,_/_/|_|\___/  
                /_/                              
    
    AI-Powered Bug Bounty Hunting Platform
    ==========================================
    """)
    
    print(f"[*] Starting BurpNake on {settings.APP_HOST}:{settings.APP_PORT}")
    print(f"[*] Ollama Model: {settings.OLLAMA_MODEL}")
    print(f"[*] Gemini: {'Configured' if settings.GEMINI_API_KEY else 'Not configured'}")
    print(f"[*] g4f: {'Enabled' if settings.G4F_ENABLED else 'Disabled'}")
    print(f"[*] Dashboard: http://{settings.APP_HOST}:{settings.APP_PORT}")
    print()
    
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
    )

if __name__ == "__main__":
    main()
