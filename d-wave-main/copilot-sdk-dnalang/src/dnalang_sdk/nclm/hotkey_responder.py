"""
OSIRIS Hotkey Response Generator — Single-Key Action Suggestions

Generates actionable hotkey response options for deduced user intent.
Enables single-key-press navigation through auto-enhanced suggestions.

DNA::}{::lang v51.843 | Agile Defense Systems | CAGE 9HUP5
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import random

@dataclass
class HotkeyOption:
    """Single hotkey action option"""
    key: str  # Single character key
    label: str
    action: str  # Command or action to execute
    hint: str  # Brief description
    category: str  # "enhance", "advance", "create", "explore", "optimize"

class HotkeyResponseGenerator:
    """
    Generates intelligent single-key hotkey options based on:
    - Detected user intent
    - Command suggestions
    - Auto-enhancement opportunities
    - Auto-advance potential
    
    Provides immediate actionable next steps without requiring typing.
    """
    
    # Hotkey mappings by intent type
    HOTKEY_MATRIX = {
        "analyze": {
            "a": HotkeyOption("a", "Analyze Deeper", "/analyze-deep", "Deep structural analysis", "enhance"),
            "d": HotkeyOption("d", "Ask Questions", "/ask-questions", "Generate diagnostic questions", "explore"),
            "c": HotkeyOption("c", "Compare Frameworks", "/compare", "Compare with alternatives", "explore"),
            "v": HotkeyOption("v", "Visualize", "/visualize", "Visual representation", "create"),
            "h": HotkeyOption("h", "History", "/history", "Review analysis history", "memory"),
            "e": HotkeyOption("e", "Enhance", "/enhance", "Auto-enhance findings", "enhance"),
        },
        "compare": {
            "d": HotkeyOption("d", "Deeper Comparison", "/compare-deep", "Multi-level analysis", "enhance"),
            "t": HotkeyOption("t", "Trade-offs", "/tradeoffs", "Cost-benefit analysis", "analyze"),
            "r": HotkeyOption("r", "Recommendation", "/recommend", "Best choice analysis", "create"),
            "c": HotkeyOption("c", "Create Hybrid", "/create-hybrid", "Combine strengths", "create"),
            "e": HotkeyOption("e", "Evolve Options", "/evolve-options", "Generate new variants", "enhance"),
            "m": HotkeyOption("m", "Metrics", "/metrics-compare", "Detailed metrics", "analyze"),
        },
        "research": {
            "d": HotkeyOption("d", "Deep Dive", "/deep-research", "Extended research", "enhance"),
            "h": HotkeyOption("h", "Hypothesis", "/hypothesis-quantum", "Generate hypotheses", "create"),
            "p": HotkeyOption("p", "Paper", "/paper-outline", "Create research paper", "create"),
            "q": HotkeyOption("q", "Quantum Research", "/quantum-hypothesis", "Quantum angle", "explore"),
            "c": HotkeyOption("c", "Cite", "/generate-citations", "Generate citations", "create"),
            "e": HotkeyOption("e", "Expand", "/expand-research", "Expand scope", "enhance"),
        },
        "create": {
            "d": HotkeyOption("d", "Draft", "/draft", "Generate draft", "create"),
            "c": HotkeyOption("c", "Code It", "/code-create", "Turn to code", "create"),
            "r": HotkeyOption("r", "Refine", "/refine", "Polish output", "enhance"),
            "e": HotkeyOption("e", "Export", "/export", "Export result", "create"),
            "t": HotkeyOption("t", "Test", "/test", "Validate output", "analyze"),
            "a": HotkeyOption("a", "Auto-enhance", "/auto-enhance", "Upgrade quality", "enhance"),
        },
        "quantum_research": {
            "q": HotkeyOption("q", "Quantum Deep", "/quantum-hypothesis", "Quantum analysis", "explore"),
            "c": HotkeyOption("c", "Circuit Design", "/circuit-design", "Design circuit", "create"),
            "b": HotkeyOption("b", "Backends", "/backends", "Available backends", "explore"),
            "a": HotkeyOption("a", "Amplitude Est", "/amplitude-estimate", "Run amplitude estimation", "analyze"),
            "s": HotkeyOption("s", "Submit", "/submit-job", "Submit quantum job", "create"),
            "e": HotkeyOption("e", "Enhancement", "/enhance-circuit", "Optimize circuit", "enhance"),
        },
        "debug": {
            "d": HotkeyOption("d", "Details", "/debug-details", "Detailed debug info", "analyze"),
            "r": HotkeyOption("r", "Repair", "/suggest-fix", "Suggested fixes", "create"),
            "t": HotkeyOption("t", "Test Fix", "/test", "Validate fix", "analyze"),
            "s": HotkeyOption("s", "Search", "/search-solutions", "Find solutions", "explore"),
            "h": HotkeyOption("h", "History", "/debug-history", "Find similar issues", "memory"),
            "e": HotkeyOption("e", "Explain Error", "/explain", "Error explanation", "analyze"),
        },
        "optimize": {
            "p": HotkeyOption("p", "Profile", "/profile", "Performance profiling", "analyze"),
            "i": HotkeyOption("i", "Improve", "/improve", "Get improvements", "enhance"),
            "b": HotkeyOption("b", "Benchmark", "/benchmark", "Compare performance", "analyze"),
            "r": HotkeyOption("r", "Refactor", "/refactor", "Code refactoring", "enhance"),
            "e": HotkeyOption("e", "Enhance", "/enhance", "Quality enhancement", "enhance"),
            "a": HotkeyOption("a", "Auto-opt", "/auto-optimize", "Automatic optimization", "enhance"),
        },
        "consciousness": {
            "p": HotkeyOption("p", "Phi Metrics", "/phi", "Integrated Information", "analyze"),
            "g": HotkeyOption("g", "Global State", "/consciousness", "Full consciousness state", "analyze"),
            "c": HotkeyOption("c", "Coherence", "/coherence", "Quantum coherence check", "analyze"),
            "e": HotkeyOption("e", "Evolve", "/evolve-consciousness", "Enhance consciousness", "enhance"),
            "v": HotkeyOption("v", "Visualize", "/visualize-phi", "Phi visualization", "create"),
            "s": HotkeyOption("s", "Status", "/status", "System consciousness status", "analyze"),
        },
        "swarm": {
            "o": HotkeyOption("o", "Organism", "/organism", "Manage organisms", "create"),
            "e": HotkeyOption("e", "Evolve", "/evolve", "Run evolution cycle", "enhance"),
            "m": HotkeyOption("m", "Mesh", "/mesh", "Create organism mesh", "create"),
            "b": HotkeyOption("b", "Breed", "/breed", "Selective breeding", "enhance"),
            "s": HotkeyOption("s", "Stats", "/swarm-stats", "Swarm statistics", "analyze"),
            "v": HotkeyOption("v", "Visualize", "/mesh-visualize", "Swarm visualization", "create"),
        },
        "question": {
            "e": HotkeyOption("e", "Explain", "/explain", "Detailed explanation", "explore"),
            "r": HotkeyOption("r", "Research", "/research", "Research topic", "explore"),
            "c": HotkeyOption("c", "Code", "/code-example", "Code example", "create"),
            "d": HotkeyOption("d", "Deep Dive", "/deep-dive", "Extended analysis", "enhance"),
            "s": HotkeyOption("s", "Similar", "/related-questions", "Related questions", "explore"),
            "h": HotkeyOption("h", "History", "/similar-history", "Historical context", "memory"),
        },
    }
    
    # Universal hotkeys available for all intents
    UNIVERSAL_HOTKEYS = {
        "?": HotkeyOption("?", "Help", "/help", "Show help", "help"),
        "m": HotkeyOption("m", "Memory", "/memory", "Review memory/history", "memory"),
        "s": HotkeyOption("s", "Status", "/status", "System status", "analyze"),
    }
    
    def generate_options(
        self, 
        intent_type: str, 
        context: Optional[str] = None,
        detected_entities: Optional[List[str]] = None,
        auto_enhance: bool = False,
        auto_advance: bool = False
    ) -> List[HotkeyOption]:
        """
        Generate hotkey options based on intent and context.
        
        Tries to provide 6-8 most relevant options for single-key navigation.
        """
        options = []
        
        # Get intent-specific options
        if intent_type in self.HOTKEY_MATRIX:
            # Get top options for this intent
            intent_options = list(self.HOTKEY_MATRIX[intent_type].values())
            
            # Add auto-enhance option if applicable
            if auto_enhance:
                options.append(HotkeyOption("a", "Auto-Enhance", "/auto-enhance", "Deepen this response", "enhance"))
            
            # Add auto-advance option if applicable
            if auto_advance:
                options.append(HotkeyOption("n", "Next Step", "/auto-advance", "Advance to next phase", "advance"))
            
            # Add entity-specific options
            if detected_entities:
                if "quantum" in detected_entities:
                    options.extend([self.HOTKEY_MATRIX["quantum_research"].get("q")] if "q" in self.HOTKEY_MATRIX.get("quantum_research", {}) else [])
                if "swarm" in detected_entities:
                    options.extend([self.HOTKEY_MATRIX["swarm"].get("o")] if "o" in self.HOTKEY_MATRIX.get("swarm", {}) else [])
            
            # Add remaining intent options
            options.extend(intent_options[:6 - len(options)])
        
        # Remove duplicates and limit total
        seen = set()
        unique_options = []
        for opt in options:
            if opt.key not in seen:
                seen.add(opt.key)
                unique_options.append(opt)
        
        # Always add help and status from universal
        for key in ["?", "m"]:
            if key not in seen and len(unique_options) < 8:
                unique_options.append(self.UNIVERSAL_HOTKEYS[key])
        
        return unique_options[:8]
    
    def format_hotkey_bar(self, options: List[HotkeyOption]) -> str:
        """
        Format hotkey options for display in TUI.
        
        Returns formatted string like: "[a] Auto-Enhance  [d] Deep Dive  [q] Quantum  [?] Help"
        """
        hotkey_strs = [f"[{opt.key}] {opt.label}" for opt in options]
        return "  ".join(hotkey_strs)
    
    def format_hotkey_list(self, options: List[HotkeyOption]) -> str:
        """
        Format hotkey options as detailed list for popup menu.
        
        Returns multi-line formatted list with hints.
        """
        lines = ["─" * 50, "HOTKEY RESPONSE OPTIONS", "─" * 50]
        
        for opt in options:
            lines.append(f"  [{opt.key}] {opt.label:<20} {opt.hint}")
        
        lines.append("─" * 50)
        return "\n".join(lines)
    
    def get_action_for_hotkey(self, hotkey: str, intent_options: List[HotkeyOption]) -> Optional[str]:
        """
        Get the action to execute for a pressed hotkey.
        
        Returns the command to run, or None if hotkey not recognized.
        """
        for opt in intent_options:
            if opt.key == hotkey:
                return opt.action
        
        # Check universal hotkeys
        if hotkey in self.UNIVERSAL_HOTKEYS:
            return self.UNIVERSAL_HOTKEYS[hotkey].action
        
        return None

# Remove the old fix that's no longer needed
