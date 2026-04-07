# OSIRIS Natural Language Quick Reference

## How It Works

Instead of typing commands like `/analyze code.py`, just talk naturally:

```
You: "analyze this code"
OSIRIS detects: Analysis intent
OSIRIS shows hotkey options below response:
┌─────────────────────────────────────────┐
│ [a] Auto-Enhance  [d] Deep Dive  [?] Help │
└─────────────────────────────────────────┘
You: Press [d] for deeper analysis (no typing needed)
```

## Supported Natural Language Patterns

### Research & Exploration
- "research quantum breakthroughs"
- "explore machine learning approaches"
- "investigate neural network architectures"
- "find recent AI developments"

### Analysis & Understanding
- "analyze this code for bugs"
- "explain how this function works"
- "break down this algorithm"
- "clarify the consciousness metrics"

### Creation & Development
- "create a Python REST API"
- "write a sorting algorithm"
- "generate a test suite"
- "design a quantum circuit"

### Debugging & Fixing
- "fix authentication error"
- "troubleshoot this issue"
- "debug the quantum backend"
- "repair broken imports"

### Optimization
- "optimize performance"
- "improve code efficiency"
- "refactor this function"
- "enhance the swarm algorithm"

## Hotkey Options

After every response, you'll see single-key options:

| Key | Typical Meanings |
|-----|-----------------|
| [a] | Auto-Enhance, Analyze Deeper, Amplitude Estimation |
| [b] | Backends, Breed, Benchmark |
| [c] | Code It, Compare, Circuit Design, Cite |
| [d] | Deep Dive, Draft, Debug Details |
| [e] | Explain, Evolve, Expand, Export, Enhancement |
| [h] | History, Hypothesis, Help |
| [i] | Improve |
| [m] | Memory (your conversation history) |
| [n] | Next Step (auto-advance) |
| [o] | Organism |
| [p] | Paper, Profile, Phi Metrics |
| [q] | Quantum Deep, Quantum Research |
| [r] | Research, Refactor, Recommend, Refine, Repair |
| [s] | Status, Stats, Submit, Search |
| [t] | Test, Trade-offs |
| [v] | Visualize |
| [?] | Help (show all available commands) |

## Entity Recognition

OSIRIS understands context keywords:

- **Quantum**: quantum physics, qubits, circuits, entanglement
- **Files**: code, file, document, script, data
- **Research**: research, paper, hypothesis, theory
- **Domains**: physics, math, biology, chemistry, AI, ML
- **Optimization**: speed, performance, efficiency

Example:
```
You: "research quantum optimization"
OSIRIS recognizes: research intent + quantum/optimization entities
OSIRIS generates hotkeys for: [q] Quantum Research, [o] Optimization focus
```

## Examples

### Example 1: Natural Research
```
You: "help me understand quantum teleportation"

OSIRIS (auto-detected: question intent):
┌────────────────────────────────────────┐
│ [e] Explain  [r] Research  [d] Deep Dive │
│ [q] Quantum Deep  [c] Code Example  [?] Help │
└────────────────────────────────────────┘
```

### Example 2: Code Creation with Enhancement
```
You: "create a function to calculate fibonacci numbers"

OSIRIS (detected: code_create + auto-enhance):
Response with code +

┌────────────────────────────────────────┐
│ [a] Auto-Enhance  [n] Optimize  [t] Test │
│ [d] Add Docstring  [r] Refactor  [?] Help │
└────────────────────────────────────────┘
```

Press [t] to automatically run tests on the generated code.

### Example 3: Research with Auto-Advance
```
You: "research latest quantum computing breakthroughs"

OSIRIS (detected: research + auto-advance enabled):
1. Clarification phase: "Searching in: quantum computing, physics domains"
2. Research phase: Shows findings
3. Analysis phase: Extracts key insights
4. Design phase: Suggests next steps

Press [n] at any point to advance to next phase.
```

## Backward Compatibility

**All slash commands still work:**
```
/research quantum physics        ← Still works
/analyze /path/to/code.py        ← Still works  
/help                             ← Still works
/memory                           ← Still works
/quantum                          ← Still works
```

Mix natural language and commands however you prefer.

## Tips & Tricks

1. **Be Natural** - Type how you'd speak. OSIRIS understands variations.
2. **Use Hotkeys** - Don't retype long commands. Press single keys instead.
3. **Check Memory** - Press [m] after research to review what you've asked.
4. **Read Hints** - The colored [AUTO-ENHANCE] and [AUTO-ADVANCE] flags show what OSIRIS will do.
5. **Press [?]** - Always shows help if you're unsure what options are available.

## Confidence Indicators

```
Intent: Analysis ████████░░  (80% confidence)
→ You'll see more hotkey options

Intent: Code Creation ██░░░░░░░░  (20% confidence)
→ OSIRIS offers fewer suggestions, maybe asks for clarification
```

Higher confidence = more specific hotkey suggestions.

## Common Patterns

| What You Say | What OSIRIS Does |
|--------------|-----------------|
| "analyze" | Prepares analysis tools |
| "compare X vs Y" | Shows side-by-side comparison |
| "research" | Searches documentation + knowledge |
| "create/write/build" | Generates code/content |
| "fix/debug/troubleshoot" | Analyzes for errors |
| "explain/clarify/understand" | Provides detailed explanation |
| "optimize/improve/enhance" | Refactors for better performance |
| "test/validate/check" | Runs validation checks |

## Error Handling

**Low confidence responses:**
```
You: "blah blah blah"
OSIRIS: "I'm not sure what you mean. Try:"
  [?] Help - Show available commands
  [m] Memory - Review past queries
  [/] Show slash commands
```

**Still works with slash commands** if natural language doesn't work for your use case.

---

**Questions?** Type `?` or press [?] for help!  
**Need commands?** Type `/help` for complete command reference.  
**Check history?** Press [m] or type `/history`.
