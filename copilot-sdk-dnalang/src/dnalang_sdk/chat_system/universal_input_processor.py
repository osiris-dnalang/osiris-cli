#!/usr/bin/env python3
"""
UNIVERSAL INPUT PROCESSOR — Handles Any Input Type
===================================================

Processes and structures diverse input types:
- Raw text & natural language
- Code snippets (Python, JavaScript, etc.)
- Error logs & stack traces
- Data files (JSON, CSV, etc.)
- Mixed/unstructured data
- Pasted documents
- Binary/hex data

Automatically detects type, parses, and prepares for analysis.
"""

from __future__ import annotations
import re
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class InputType(Enum):
    """Detected input types"""
    NATURAL_LANGUAGE = "text"
    PYTHON_CODE = "python"
    JAVASCRIPT_CODE = "javascript"
    JAVA_CODE = "java"
    CSHARP_CODE = "csharp"
    CPP_CODE = "cpp"
    RUST_CODE = "rust"
    SQL_CODE = "sql"
    JSON_DATA = "json"
    CSV_DATA = "csv"
    YAML_DATA = "yaml"
    ERROR_LOG = "error_log"
    STACK_TRACE = "stack_trace"
    COMMAND_OUTPUT = "command_output"
    MARKDOWN_DOC = "markdown"
    HTML_DOC = "html"
    MIXED = "mixed"
    UNKNOWN = "unknown"


@dataclass
class DetectedInput:
    """Result of input detection and parsing"""
    raw_text: str
    detected_type: InputType
    parsed_content: Any = None
    language: Optional[str] = None
    structure_info: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.detected_type.value,
            "language": self.language,
            "confidence": self.confidence,
            "structure_info": self.structure_info,
            "errors": self.errors,
            "metadata": self.metadata,
        }


class UniversalInputProcessor:
    """
    Processes any type of input and extracts actionable structure.
    """
    
    def __init__(self):
        # Language-specific patterns
        self.python_patterns = [
            r'^\s*def\s+\w+\s*\(',  # function definition
            r'^\s*class\s+\w+',      # class definition
            r'^\s*import\s+',        # import statement
            r'^\s*from\s+\w+\s+import',  # from import
        ]
        
        self.js_patterns = [
            r'^\s*function\s+\w+\s*\(',
            r'^\s*const\s+\w+\s*=',
            r'^\s*let\s+\w+\s*=',
            r'^\s*class\s+\w+\s*{',
        ]
        
        self.error_patterns = [
            r'(?:Error|Exception|Traceback|Errno)',
            r'(?:FAIL|ERROR|CRITICAL)',
            r'at\s+\w+\.py:\d+',  # Python traceback
            r'at\s+\w+\.js:\d+',  # JS traceback
        ]
    
    def process(self, input_text: str) -> DetectedInput:
        """
        Process arbitrary input and detect type/structure.
        
        Args:
            input_text: Raw user input
        
        Returns:
            DetectedInput object with parsed content and metadata
        """
        input_text = input_text.strip()
        
        if not input_text:
            return DetectedInput(
                raw_text="",
                detected_type=InputType.UNKNOWN,
                confidence=0.0,
            )
        
        # Try detection in order of likelihood
        detected = (
            self._try_json(input_text) or
            self._try_code(input_text) or
            self._try_error_log(input_text) or
            self._try_csv(input_text) or
            self._try_markdown(input_text) or
            self._classify_text(input_text)
        )
        
        return detected
    
    def _try_json(self, text: str) -> Optional[DetectedInput]:
        """Try to parse as JSON"""
        # Look for JSON indicators
        if not (text.strip().startswith('{') or text.strip().startswith('[')):
            return None
        
        try:
            parsed = json.loads(text)
            info = {
                "keys": list(parsed.keys()) if isinstance(parsed, dict) else "list",
                "depth": self._measure_json_depth(parsed),
                "size": len(text),
            }
            
            return DetectedInput(
                raw_text=text,
                detected_type=InputType.JSON_DATA,
                parsed_content=parsed,
                language="json",
                structure_info=info,
                confidence=0.95,
            )
        except json.JSONDecodeError:
            return None
    
    def _try_code(self, text: str) -> Optional[DetectedInput]:
        """Try to detect programming language"""
        lines = text.split('\n')
        
        # Python detection
        python_score = sum(1 for line in lines if re.match(
            '|'.join(self.python_patterns), line))
        if python_score > 0:
            return DetectedInput(
                raw_text=text,
                detected_type=InputType.PYTHON_CODE,
                language="python",
                structure_info=self._analyze_code(text),
                confidence=min(0.95, 0.7 + (python_score * 0.1)),
            )
        
        # JavaScript detection
        js_score = sum(1 for line in lines if re.match(
            '|'.join(self.js_patterns), line))
        if js_score > 0:
            return DetectedInput(
                raw_text=text,
                detected_type=InputType.JAVASCRIPT_CODE,
                language="javascript",
                structure_info=self._analyze_code(text),
                confidence=min(0.95, 0.7 + (js_score * 0.1)),
            )
        
        # SQL detection
        if any(keyword in text.upper() for keyword in ["SELECT", "INSERT", "UPDATE", "DELETE"]):
            return DetectedInput(
                raw_text=text,
                detected_type=InputType.SQL_CODE,
                language="sql",
                structure_info=self._analyze_code(text),
                confidence=0.85,
            )
        
        # General code detection (braces, semicolons, indentation)
        code_indicators = (
            text.count('{') > 0 or
            text.count('[') > 2 or
            text.count(';') > 2 or
            any(line.startswith('    ') for line in lines)
        )
        
        if code_indicators:
            return DetectedInput(
                raw_text=text,
                detected_type=InputType.MIXED,  # Code + text
                structure_info=self._analyze_code(text),
                confidence=0.6,
            )
        
        return None
    
    def _try_error_log(self, text: str) -> Optional[DetectedInput]:
        """Try to detect error logs/stack traces"""
        error_count = sum(1 for pattern in self.error_patterns
                         if re.search(pattern, text))
        
        if error_count > 0:
            info = self._parse_error_log(text)
            input_type = (InputType.STACK_TRACE if "traceback" in text.lower()
                         else InputType.ERROR_LOG)
            
            return DetectedInput(
                raw_text=text,
                detected_type=input_type,
                structure_info=info,
                confidence=min(0.95, 0.7 + (error_count * 0.1)),
            )
        
        return None
    
    def _try_csv(self, text: str) -> Optional[DetectedInput]:
        """Try to parse CSV"""
        lines = text.split('\n')
        if len(lines) < 2:
            return None
        
        # Check if looks like CSV
        first_line = lines[0]
        if not (',' in first_line or '\t' in first_line):
            return None
        
        delim = ',' if ',' in first_line else '\t'
        parts = first_line.split(delim)
        
        if len(parts) > 1:
            info = {
                "columns": len(parts),
                "rows": len(lines) - 1,
                "headers": [h.strip() for h in parts],
            }
            
            return DetectedInput(
                raw_text=text,
                detected_type=InputType.CSV_DATA,
                structure_info=info,
                confidence=0.85,
            )
        
        return None
    
    def _try_markdown(self, text: str) -> Optional[DetectedInput]:
        """Detect markdown documents"""
        if '#' in text[:100] or '```' in text:
            info = {
                "has_headings": bool(re.search(r'^#+\s', text, re.MULTILINE)),
                "has_code_blocks": bool(re.search(r'```', text)),
                "has_links": bool(re.search(r'\[.*?\]\(.*?\)', text)),
            }
            
            return DetectedInput(
                raw_text=text,
                detected_type=InputType.MARKDOWN_DOC,
                language="markdown",
                structure_info=info,
                confidence=0.8,
            )
        
        return None
    
    def _classify_text(self, text: str) -> DetectedInput:
        """Classify as natural language or command output"""
        # Check for command output characteristics
        if re.search(r'^\$|^>|^#\s*Command', text, re.MULTILINE):
            return DetectedInput(
                raw_text=text,
                detected_type=InputType.COMMAND_OUTPUT,
                structure_info=self._parse_command_output(text),
                confidence=0.8,
            )
        
        # Default to natural language
        return DetectedInput(
            raw_text=text,
            detected_type=InputType.NATURAL_LANGUAGE,
            structure_info=self._analyze_text(text),
            confidence=0.7,
        )
    
    def _analyze_code(self, code: str) -> Dict[str, Any]:
        """Analyze code structure"""
        lines = code.split('\n')
        non_empty_lines = [l for l in lines if l.strip()]
        
        # Count syntax elements
        functions = len(re.findall(r'def\s+\w+|function\s+\w+', code))
        classes = len(re.findall(r'class\s+\w+', code))
        comments = len(re.findall(r'#.*$|//.*$', code, re.MULTILINE))
        
        return {
            "lines": len(non_empty_lines),
            "functions": functions,
            "classes": classes,
            "comments": comments,
            "comment_ratio": comments / max(1, len(non_empty_lines)),
        }
    
    def _parse_error_log(self, text: str) -> Dict[str, Any]:
        """Parse error log structure"""
        # Extract error type
        error_match = re.search(r'(Error|Exception|Warning|FAIL|CRITICAL):\s*(.+)', text)
        error_type = error_match.group(1) if error_match else "Unknown"
        error_msg = error_match.group(2).strip() if error_match else ""
        
        # Extract stack frames (Python style)
        frames = re.findall(r'File\s+"(.+?)".+?line\s+(\d+)', text)
        
        # Extract line numbers
        lines = re.findall(r':\d+:', text)
        
        return {
            "error_type": error_type,
            "error_message": error_msg,
            "stack_frames": len(frames),
            "affected_files": len(set(f[0] for f in frames)),
            "line_count": len(lines),
        }
    
    def _parse_command_output(self, text: str) -> Dict[str, Any]:
        """Parse command output"""
        lines = text.split('\n')
        
        return {
            "lines": len(lines),
            "has_errors": any(word in text.lower() for word in ["error", "fail", "failed"]),
            "has_warnings": any(word in text.lower() for word in ["warn", "warning"]),
            "exit_code": self._extract_exit_code(text),
        }
    
    def _extract_exit_code(self, text: str) -> Optional[int]:
        """Extract exit code if present"""
        match = re.search(r'exit\s+code\s+(\d+)|returned\s+(\d+)', text, re.IGNORECASE)
        if match:
            return int(match.group(1) or match.group(2))
        return None
    
    def _analyze_text(self, text: str) -> Dict[str, Any]:
        """Analyze natural language text"""
        words = text.split()
        sentences = re.split(r'[.!?]+', text)
        
        return {
            "word_count": len(words),
            "sentence_count": len([s for s in sentences if s.strip()]),
            "avg_words_per_sentence": len(words) / max(1, len(sentences)),
            "includes_questions": '?' in text,
            "includes_code_refs": any(c in text for c in ['`', 'def ', 'class ', 'function']),
        }
    
    def _measure_json_depth(self, obj: Any, depth: int = 0) -> int:
        """Measure JSON nesting depth"""
        if isinstance(obj, dict):
            if not obj:
                return depth
            return max(self._measure_json_depth(v, depth + 1) for v in obj.values())
        elif isinstance(obj, list):
            if not obj:
                return depth
            return max(self._measure_json_depth(item, depth + 1) for item in obj)
        else:
            return depth
    
    def summarize(self, detected: DetectedInput) -> str:
        """Generate a summary description of detected input"""
        type_name = detected.detected_type.value
        info_parts = []
        
        for key, value in detected.structure_info.items():
            if isinstance(value, (int, float)):
                info_parts.append(f"{key}={value}")
            elif isinstance(value, bool):
                if value:
                    info_parts.append(key)
        
        info_str = ", ".join(info_parts) if info_parts else ""
        
        if detected.language:
            type_name = f"{detected.language} {type_name}"
        
        if detected.errors:
            return f"{type_name} (⚠ {len(detected.errors)} issues) [{info_str}]"
        
        return f"{type_name} (confidence: {detected.confidence:.0%}) [{info_str}]"


# Factory function
def create_input_processor() -> UniversalInputProcessor:
    """Create an input processor"""
    return UniversalInputProcessor()
