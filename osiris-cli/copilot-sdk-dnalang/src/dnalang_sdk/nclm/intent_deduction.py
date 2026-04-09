"""
OSIRIS Intent Deduction Engine — Conversational AI Intent Recognition

Deduces user intent from natural language without explicit command structure.
Provides intelligent suggestions and auto-routing for optimal experience.

DNA::}{::lang v51.843 | Agile Defense Systems | CAGE 9HUP5
"""

from typing import Dict, List, Tuple, Optional
import re
from dataclasses import dataclass

@dataclass
class IntentMatch:
    """Matched user intent"""
    intent_type: str  # "analyze", "research", "create", "optimize", etc.
    confidence: float  # 0.0-1.0
    detected_entities: List[str]
    suggested_commands: List[str]
    auto_enhance: bool
    auto_advance: bool

class IntentDeductionEngine:
    """
    Natural language intent deduction without command syntax required.
    Automatically detects what the user wants and suggests optimal execution paths.
    """
    
    # Intent patterns: (pattern, intent_type, auto_enhance, auto_advance)
    INTENT_PATTERNS = {
        # Analysis intents
        "analyze|explain|breakdown|understand|clarify|describe|what is": (
            "analyze", True, False
        ),
        "compare|versus|vs|difference|contrast|similar": (
            "compare", True, True
        ),
        "diagnose|debug|fix|troubleshoot|error|problem|broken": (
            "debug", True, False
        ),
        
        # Research intents
        "research|investigate|explore|discover|search|find|seek": (
            "research", True, True
        ),
        "hypothesis|theory|propose|suggest|could": (
            "hypothesis", True, True
        ),
        "quantum": (
            "quantum_research", True, True
        ),
        
        # Creation intents
        "create|generate|write|make|build|design|architect": (
            "create", True, False
        ),
        "code|implement|function|script|program": (
            "code_create", True, False
        ),
        "document|paper|essay|article|report": (
            "document", True, False
        ),
        
        # Optimization intents
        "optimize|improve|enhance|better|faster|faster|more efficient": (
            "optimize", True, True
        ),
        "refactor|restructure|reorganize": (
            "optimize", True, False
        ),
        
        # Memory/Learning intents
        "remember|memory|recall|history|past": (
            "memory", False, False
        ),
        "learn|study|read|understand deeply": (
            "learning", True, True
        ),
        
        # Execution intents
        "run|execute|deploy|launch|start": (
            "execute", False, False
        ),
        "test|check|validate|verify": (
            "test", False, False
        ),
        
        # Interaction intents
        "ask|question|query|know|tell": (
            "question", False, False
        ),
        "help|guide|tutorial|how|instruction": (
            "help", False, False
        ),
        
        # System intents
        "status|state|condition|metrics|health": (
            "status", False, False
        ),
        "consciousness|aware|phi|quantum state": (
            "consciousness", False, False
        ),
        
        # Swarm intents
        "swarm|organism|evolve|mutate|breed": (
            "swarm", True, True
        ),
    }
    
    # Entity patterns
    ENTITY_PATTERNS = {
        "file": r"file|document|code|script|text|data",
        "quantum": r"quantum|qubit|circuit|algorithm|backend",
        "research": r"research|paper|hypothesis|theory|discovery",
        "domain": r"physics|math|biology|chemistry|astronomy|ai|ml",
        "optimization": r"speed|performance|efficiency|optimize|improve",
        "consciousness": r"consciousness|aware|phi|coherence|intelligence",
    }
    
    def deduct_intent(self, user_input: str) -> IntentMatch:
        """
        Deduct user intent from natural language input.
        
        Returns:
            IntentMatch with detected intent and suggestions
        """
        user_input_lower = user_input.lower()
        
        best_match = None
        best_confidence = 0.0
        
        # Find best matching intent pattern
        for pattern, (intent_type, auto_enhance, auto_advance) in self.INTENT_PATTERNS.items():
            if re.search(pattern, user_input_lower):
                # Calculate confidence based on pattern specificity
                pattern_parts = pattern.split("|")
                matched_parts = sum(1 for p in pattern_parts if p in user_input_lower)
                confidence = min(1.0, matched_parts / len(pattern_parts))
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = (intent_type, auto_enhance, auto_advance)
        
        # Detect entities
        detected_entities = self._detect_entities(user_input_lower)
        
        # Default to question if no pattern matched
        if best_match is None:
            intent_type, auto_enhance, auto_advance = "question", False, False
            best_confidence = 0.3
        else:
            intent_type, auto_enhance, auto_advance = best_match
        
        # Generate suggestions based on intent and entities
        suggestions = self._generate_suggestions(intent_type, detected_entities, user_input)
        
        return IntentMatch(
            intent_type=intent_type,
            confidence=best_confidence,
            detected_entities=detected_entities,
            suggested_commands=suggestions,
            auto_enhance=auto_enhance,
            auto_advance=auto_advance
        )
    
    def _detect_entities(self, text: str) -> List[str]:
        """Detect key entities in user input"""
        entities = []
        
        for entity_type, pattern in self.ENTITY_PATTERNS.items():
            if re.search(pattern, text):
                entities.append(entity_type)
        
        return entities
    
    def _generate_suggestions(self, intent_type: str, entities: List[str], original_input: str) -> List[str]:
        """Generate command suggestions based on intent and entities"""
        suggestions = []
        
        # Intent-based suggestions
        intent_commands = {
            "analyze": ["/analyze", "/explain", "/consciousness"],
            "compare": ["/compare", "/analyze", "/research"],
            "debug": ["/fix", "/analyze", "/test"],
            "research": ["/research", "/hypothesis", "/quantum"],
            "hypothesis": ["/hypothesis", "/quantum-hypothesis", "/research"],
            "quantum_research": ["/quantum", "/quantum-hypothesis", "/backends"],
            "create": ["/create", "/write", "/ingest"],
            "code_create": ["/create", "/run", "/test"],
            "document": ["/paper", "/write", "/export"],
            "optimize": ["/optimize", "/analyze", "/enhance"],
            "memory": ["/memory", "/history", "/session"],
            "learning": ["/understand", "/research", "/memory"],
            "execute": ["/run", "/deploy", "/test"],
            "test": ["/test", "/run", "/analyze"],
            "question": ["/ask", "/help", "/explain"],
            "help": ["/help", "/demo", "/guide"],
            "status": ["/status", "/metrics", "/consciousness"],
            "consciousness": ["/consciousness", "/phi", "/status"],
            "swarm": ["/swarm", "/organism", "/evolve"],
        }
        
        suggestions.extend(intent_commands.get(intent_type, []))
        
        # Entity-specific suggestions
        if "quantum" in entities:
            suggestions.extend(["/quantum", "/backends", "/submit"])
        if "research" in entities:
            suggestions.extend(["/research", "/paper", "/hypothesis"])
        if "file" in entities:
            suggestions.extend(["/read", "/analyze", "/edit"])
        if "swarm" in intent_type or "organism" in entities:
            suggestions.extend(["/organism", "/evolution", "/mesh"])
        
        # Remove duplicates and limit to 6 suggestions
        return list(dict.fromkeys(suggestions))[:6]
    
    def get_intent_explanation(self, intent: IntentMatch) -> str:
        """Get human-readable explanation of detected intent"""
        confidence_indicator = "█" * int(intent.confidence * 10)
        return f"Detected: {intent.intent_type.replace('_', ' ').title()} [{confidence_indicator}]"
