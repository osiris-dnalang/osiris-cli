"""
OSIRIS Natural Language Middleware — Conversational Intent Router

Integrates intent deduction and hotkey responses to provide chatbot-like
conversational interface without requiring command syntax.

DNA::}{::lang v51.843 | Agile Defense Systems | CAGE 9HUP5
"""

from typing import Tuple, Optional, List, Dict
from dataclasses import dataclass
import re

from .intent_deduction import IntentDeductionEngine, IntentMatch
from .hotkey_responder import HotkeyResponseGenerator, HotkeyOption

@dataclass
class ConversationalResponse:
    """Response from natural language middleware"""
    content: str  # Main response content
    command: str  # Command to execute (e.g., "/analyze")
    hotkey_options: List[HotkeyOption]  # Available single-key actions
    hotkey_bar: str  # Formatted hotkey bar for display
    confidence: float  # Confidence in intent detection (0.0-1.0)
    intent: str  # Detected intent type
    auto_enhance: bool  # Whether response should be auto-enhanced
    auto_advance: bool  # Whether response should auto-advance

class NaturalLanguageMiddleware:
    """
    Converts natural language input into structured intent + commands + hotkeys.
    
    Allows users to:
    - Type naturally without slash commands: "explore quantum physics"
    - Get automatic intent detection: "research" detected
    - Receive actionable hotkey options: [d] Deep Dive, [q] Quantum, etc.
    - Enable auto-enhancement and auto-advancement
    
    Maintains backward compatibility with slash commands.
    """
    
    def __init__(self):
        self.intent_engine = IntentDeductionEngine()
        self.hotkey_generator = HotkeyResponseGenerator()
        self.command_cache: Dict[str, str] = {}  # Cache for repeated intents
        
    def process_user_input(self, user_input: str) -> ConversationalResponse:
        """
        Process natural language user input and return structured response.
        
        Flow:
        1. Check if input is slash command (pass through directly)
        2. Deduct intent from natural language
        3. Generate suggested commands
        4. Create hotkey options
        5. Format response with hotkey bar
        
        Args:
            user_input: User's natural language input (e.g., "analyze this code")
            
        Returns:
            ConversationalResponse with command, intent, and hotkey options
        """
        
        # Check if input is already a slash command
        if user_input.strip().startswith("/"):
            return self._handle_slash_command(user_input)
        
        # Deduct intent from natural language
        intent_match = self.intent_engine.deduct_intent(user_input)
        
        # Select primary command from suggestions
        primary_command = (
            intent_match.suggested_commands[0] 
            if intent_match.suggested_commands 
            else "/ask"
        )
        
        # Generate hotkey options
        hotkey_options = self.hotkey_generator.generate_options(
            intent_type=intent_match.intent_type,
            context=user_input,
            detected_entities=intent_match.detected_entities,
            auto_enhance=intent_match.auto_enhance,
            auto_advance=intent_match.auto_advance
        )
        
        # Format response
        hotkey_bar = self.hotkey_generator.format_hotkey_bar(hotkey_options)
        
        # Build initial response hint
        response_content = self._build_response_hint(
            intent_match, 
            user_input,
            primary_command
        )
        
        return ConversationalResponse(
            content=response_content,
            command=primary_command,
            hotkey_options=hotkey_options,
            hotkey_bar=hotkey_bar,
            confidence=intent_match.confidence,
            intent=intent_match.intent_type,
            auto_enhance=intent_match.auto_enhance,
            auto_advance=intent_match.auto_advance
        )
    
    def _handle_slash_command(self, user_input: str) -> ConversationalResponse:
        """Handle direct slash command input"""
        command = user_input.strip()
        
        # Extract command type for hotkey generation
        command_type = command.split()[0].lstrip("/")
        
        # Map command to intent for hotkey suggestions
        intent_mapping = {
            "analyze": "analyze",
            "quantum": "quantum_research",
            "research": "research",
            "create": "create",
            "optimize": "optimize",
            "help": "help",
            "status": "status",
            "consciousness": "consciousness",
            "organism": "swarm",
        }
        
        intent_type = intent_mapping.get(command_type, "question")
        
        # Generate hotkey options for slash command context
        hotkey_options = self.hotkey_generator.generate_options(
            intent_type=intent_type,
            context=command
        )
        
        hotkey_bar = self.hotkey_generator.format_hotkey_bar(hotkey_options)
        
        return ConversationalResponse(
            content=f"Executing: {command}",
            command=command,
            hotkey_options=hotkey_options,
            hotkey_bar=hotkey_bar,
            confidence=1.0,
            intent=intent_type,
            auto_enhance=False,
            auto_advance=False
        )
    
    def _build_response_hint(
        self, 
        intent_match: IntentMatch, 
        original_input: str,
        command: str
    ) -> str:
        """Build initial response hint before command execution"""
        
        intent_explanation = self.intent_engine.get_intent_explanation(intent_match)
        
        # Build hint based on detected entities
        entity_hints = []
        if "quantum" in intent_match.detected_entities:
            entity_hints.append("quantum computational angle")
        if "swarm" in intent_match.detected_entities:
            entity_hints.append("multi-agent swarm perspective")
        if "consciousness" in intent_match.detected_entities:
            entity_hints.append("integrated information (Φ) metrics")
        if "file" in intent_match.detected_entities:
            entity_hints.append("data/file processing")
        if "research" in intent_match.detected_entities:
            entity_hints.append("research methodology")
        
        hint_text = ""
        if entity_hints:
            hint_text = " Analyzing with: " + ", ".join(entity_hints)
        
        return f"{intent_explanation}{hint_text}\n→ Running: {command}"
    
    def extract_intent_entities(self, user_input: str) -> Tuple[str, List[str]]:
        """
        Quick extraction of intent and entities without full processing.
        
        Useful for routing/filtering decisions.
        """
        intent_match = self.intent_engine.deduct_intent(user_input)
        return intent_match.intent_type, intent_match.detected_entities
    
    def enhance_response_with_hotkeys(
        self, 
        response_content: str, 
        conversation_response: ConversationalResponse
    ) -> str:
        """
        Wrap response content with hotkey bar.
        
        Args:
            response_content: The main response text
            conversation_response: ConversationalResponse with hotkeys
            
        Returns:
            Response text with hotkey bar appended
        """
        enhanced = f"{response_content}\n\n┌{'─' * 60}┐\n"
        enhanced += f"│ {conversation_response.hotkey_bar:<58} │\n"
        enhanced += "└" + "─" * 60 + "┘"
        
        return enhanced


class AutoEnhancer:
    """
    Automatically enhances responses by deepening analysis.
    
    When auto_enhance=True, progressively adds:
    - Deeper analysis layers
    - Additional perspectives
    - Validation checks
    - Enhancement suggestions
    """
    
    @staticmethod
    def should_enhance(
        confidence: float,
        intent_type: str,
        auto_enhance_flag: bool
    ) -> bool:
        """Determine if response should be auto-enhanced"""
        return auto_enhance_flag or confidence > 0.8
    
    @staticmethod
    def get_enhancement_layers(intent_type: str) -> List[str]:
        """Get progressive enhancement layers for intent"""
        enhancements = {
            "analyze": [
                "/analyze-deep",    # Deeper structural analysis
                "/ask-questions",   # Generate diagnostic questions
                "/visualize",       # Visualize findings
            ],
            "research": [
                "/deep-research",   # Extended research scope
                "/hypothesis",      # Generate hypotheses
                "/validate",        # Validate findings
            ],
            "create": [
                "/refine",          # Polish and refine
                "/validate",        # Validation checks
                "/optimize",        # Optimization pass
            ],
            "quantum": [
                "/quantum-deep",    # Quantum-specific analysis
                "/circuit-design",  # Circuit design suggestions
                "/backends",        # Backend recommendations
            ],
        }
        return enhancements.get(intent_type, [])


class AutoAdvancer:
    """
    Automatically advances conversation through solution phases.
    
    Progression path:
    1. Understanding → 2. Analysis → 3. Design → 4. Implementation → 5. Optimization
    
    When auto_advance=True, moves through phases automatically.
    """
    
    ADVANCEMENT_PHASES = [
        {
            "phase": "clarify",
            "command": "/ask-questions",
            "description": "Clarify requirements"
        },
        {
            "phase": "analyze",
            "command": "/analyze",
            "description": "Deep analysis"
        },
        {
            "phase": "design",
            "command": "/design",
            "description": "Solution design"
        },
        {
            "phase": "implement",
            "command": "/create",
            "description": "Implementation"
        },
        {
            "phase": "optimize",
            "command": "/optimize",
            "description": "Optimization & refinement"
        },
    ]
    
    @staticmethod
    def get_next_phase(current_phase: Optional[str] = None) -> Dict:
        """Get next phase in auto-advancement"""
        if not current_phase:
            return AutoAdvancer.ADVANCEMENT_PHASES[0]
        
        for i, phase_info in enumerate(AutoAdvancer.ADVANCEMENT_PHASES):
            if phase_info["phase"] == current_phase:
                if i + 1 < len(AutoAdvancer.ADVANCEMENT_PHASES):
                    return AutoAdvancer.ADVANCEMENT_PHASES[i + 1]
        
        return AutoAdvancer.ADVANCEMENT_PHASES[-1]
    
    @staticmethod
    def should_advance_to_next(
        current_phase: str,
        confidence: float,
        auto_advance_flag: bool
    ) -> bool:
        """Determine if conversation should auto-advance to next phase"""
        return auto_advance_flag and confidence > 0.7
