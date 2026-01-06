from difflib import SequenceMatcher
from app.remedy_database import REMEDIES

class RemedyMatcher:
    def __init__(self):
        self.remedies = REMEDIES
    
    def _calculate_match_score(self, user_symptoms: str, remedy: dict) -> float:
        """Calculate match score using keyword matching and fuzzy matching."""
        user_words = set(user_symptoms.lower().split())
        user_symptoms_lower = user_symptoms.lower()
        
        score = 0
        max_possible = len(remedy["symptoms"]) * 2
        
        for symptom in remedy["symptoms"]:
            symptom_lower = symptom.lower()
            
            # Direct substring match (highest weight)
            if symptom_lower in user_symptoms_lower:
                score += 2
            # Partial word match
            elif any(word in symptom_lower or symptom_lower in word for word in user_words):
                score += 1.5
            # Fuzzy match
            else:
                for word in user_words:
                    if len(word) > 3:
                        ratio = SequenceMatcher(None, word, symptom_lower).ratio()
                        if ratio > 0.7:
                            score += ratio
                            break
        
        # Check description
        desc_words = remedy["description"].lower().split()
        for word in user_words:
            if len(word) > 3 and word in desc_words:
                score += 0.5
        
        # Normalize score to percentage
        return min((score / max_possible) * 100, 100)
    
    def find_matching_remedies(self, user_symptoms: str, top_k: int = 5):
        """Find top matching remedies for given symptoms."""
        results = []
        
        for remedy in self.remedies:
            score = self._calculate_match_score(user_symptoms, remedy)
            if score > 0:
                results.append({
                    "name": remedy["name"],
                    "match_score": round(score, 1),
                    "description": remedy["description"],
                    "key_symptoms": remedy["symptoms"][:5],
                    "potency": remedy["potency"],
                    "modalities": remedy.get("modalities", {})
                })
        
        # Sort by score descending
        results.sort(key=lambda x: x["match_score"], reverse=True)
        
        return results[:top_k]
