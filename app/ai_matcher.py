import os
import json
import requests
from app.remedy_database import REMEDIES

# Set API key permanently
GEMINI_API_KEY = "AIzaSyAg6XW8V7tvl2pJPQvGruoYnVM1A6NreTk"

class AIRemedyMatcher:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY") or GEMINI_API_KEY
        if self.api_key:
            self.ai_enabled = True
            # Use gemini-1.5-flash (more reliable)
            self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        else:
            self.ai_enabled = False
            print("⚠️ GEMINI_API_KEY not set. Using keyword matching.")
        
        self.remedy_list = "\n".join([
            f"- {r['name']}: {r['description']} Key symptoms: {', '.join(r['symptoms'][:8])}"
            for r in REMEDIES
        ])
    
    def find_matching_remedies(self, user_symptoms: str):
        if not self.ai_enabled:
            from app.remedy_matcher import RemedyMatcher
            return RemedyMatcher().find_matching_remedies(user_symptoms)
        
        prompt = f"""You are an expert homeopathic practitioner with deep knowledge of Materia Medica.

Analyze these symptoms and suggest the top 5 matching homeopathic remedies:

SYMPTOMS: {user_symptoms}

AVAILABLE REMEDIES:
{self.remedy_list}

Return ONLY a JSON array with this exact format (no other text):
[
  {{"name": "Arnica Montana", "match_score": 90, "reason": "Matches because..."}},
  {{"name": "Belladonna", "match_score": 75, "reason": "Matches because..."}}
]

Important:
- Use exact remedy names from the list
- match_score: 0-100 based on how well symptoms match
- Sort by match_score (highest first)
- Give specific reasons based on the symptoms provided
"""
        
        try:
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "topP": 0.8,
                    "maxOutputTokens": 1024
                }
            }
            
            response = requests.post(self.api_url, json=payload, timeout=30)
            
            if response.status_code != 200:
                print(f"API Error: {response.status_code} - {response.text}")
                from app.remedy_matcher import RemedyMatcher
                return RemedyMatcher().find_matching_remedies(user_symptoms)
            
            data = response.json()
            
            # Extract text from response
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            print(f"AI Response: {text[:200]}...")  # Debug log
            
            # Clean markdown formatting
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            text = text.strip()
            results = json.loads(text)
            
            # Enrich with full remedy data
            enriched_results = []
            for result in results:
                remedy_found = False
                for r in REMEDIES:
                    if r["name"].lower() == result.get("name", "").lower():
                        enriched_results.append({
                            "name": r["name"],
                            "match_score": result.get("match_score", 50),
                            "reason": result.get("reason", ""),
                            "description": r["description"],
                            "key_symptoms": r["symptoms"][:5],
                            "potency": r["potency"],
                            "modalities": r.get("modalities", {})
                        })
                        remedy_found = True
                        break
                
                # If remedy not in database, still include basic info
                if not remedy_found and result.get("name"):
                    enriched_results.append({
                        "name": result["name"],
                        "match_score": result.get("match_score", 50),
                        "reason": result.get("reason", ""),
                        "description": "Remedy suggested by AI",
                        "key_symptoms": [],
                        "potency": "Consult a practitioner",
                        "modalities": {"worse": [], "better": []}
                    })
            
            return enriched_results[:5] if enriched_results else self._fallback(user_symptoms)
            
        except json.JSONDecodeError as e:
            print(f"JSON Parse Error: {e}")
            return self._fallback(user_symptoms)
        except Exception as e:
            print(f"AI Error: {e}")
            return self._fallback(user_symptoms)
    
    def _fallback(self, user_symptoms: str):
        """Fallback to keyword matching"""
        from app.remedy_matcher import RemedyMatcher
        return RemedyMatcher().find_matching_remedies(user_symptoms)
