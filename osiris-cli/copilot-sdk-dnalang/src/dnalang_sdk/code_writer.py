#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════════════════╗
║     ██████╗ ██████╗  ██████╗██╗  ██╗██████╗ ██╗████████╗                                  ║
║    ██╔════╝██╔═══██╗██╔════╝██║ ██╔╝██╔══██╗██║╚══██╔══╝                                  ║
║    ██║     ██║   ██║██║     █████╔╝ ██████╔╝██║   ██║                                     ║
║    ██║     ██║   ██║██║     ██╔═██╗ ██╔═══╝ ██║   ██║                                     ║
║    ╚██████╗╚██████╔╝╚██████╗██║  ██╗██║     ██║   ██║                                     ║
║     ╚═════╝ ╚═════╝  ╚═════╝╚═╝  ╚═╝╚═╝     ╚═╝   ╚═╝                                     ║
║                                                                                          ║
║    COCKPIT CODE WRITER v2.0 — Advanced NLP → Filesystem Code Writer                      ║
║    Capabilities: Write, Edit, Execute, Deploy across PC, Meshnet, Scimitar Elite         ║
║                                                                                          ║
║    Author: Devin Phillip Davis | Agile Defense Systems, LLC (CAGE: 9HUP5)                ║
╚══════════════════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import re
import json
import subprocess
import tempfile
import difflib
import shutil
# socket removed in offline-only mode on purpose
import hashlib
import signal
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple, Callable
from enum import Enum, auto
import time
import threading
import ast
import textwrap

# ═══════════════════════════════════════════════════════════════════════════════
# PHYSICAL CONSTANTS (Immutable)
# ═══════════════════════════════════════════════════════════════════════════════

LAMBDA_PHI = 2.176435e-8      # Universal Memory Constant [s⁻¹]
PHI_THRESHOLD = 0.7734        # Consciousness Threshold (POC)
GAMMA_FIXED = 0.092           # Fixed-point decoherence
GOLDEN_RATIO = 1.618033988749895
VERSION = "2.0.0"

# ═══════════════════════════════════════════════════════════════════════════════
# COLORS & UTILS
# ═══════════════════════════════════════════════════════════════════════════════

class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    WHITE = "\033[97m"

def c(text: str, color: str) -> str:
    return f"{color}{text}{C.RESET}"

def now() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTION TARGET ENUM
# ═══════════════════════════════════════════════════════════════════════════════

class ExecutionTarget(Enum):
    LOCAL = auto()          # This PC
    MESHNET = auto()        # 3-Node Mesh (PC, Phone, API)
    PHONE = auto()          # Samsung Fold 7 via ADB
    SCIMITAR = auto()       # Scimitar Elite mouse macros
    IDE = auto()            # VSCode / Zed / Claude Code
    REMOTE_API = auto()     # Σ-brain node


class FileAction(Enum):
    CREATE = auto()
    EDIT = auto()
    DELETE = auto()
    RENAME = auto()
    APPEND = auto()


# ═══════════════════════════════════════════════════════════════════════════════
# CODE WRITER ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class WriteOperation:
    """Represents a single file write operation."""
    filepath: Path
    content: str
    action: FileAction
    language: str
    description: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    backup_path: Optional[Path] = None
    success: bool = False
    error: Optional[str] = None


class CodeWriter:
    """
    Writes code to filesystem with safety features:
    - Automatic backups before edits
    - Syntax validation before write
    - Diff preview
    - Undo capability
    - Permission checking
    """

    def __init__(self, workspace: Path = None):
        self.workspace = workspace or Path.home() / ".sovereign"
        self.backup_dir = self.workspace / ".backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.write_history: List[WriteOperation] = []
        self.undo_stack: List[WriteOperation] = []
        self.max_history = 100

        # Allowed write directories (security)
        self.allowed_dirs = [
            Path.home(),
            Path("/tmp"),
            Path.home() / "Downloads",
            Path.home() / ".sovereign",
        ]

        # Dangerous patterns to prevent
        self.dangerous_patterns = [
            r'rm\s+-rf\s+/',
            r'sudo\s+rm',
            r':(){:|:&};:',  # Fork bomb
            r'>\s*/dev/sd',
            r'mkfs\.',
            r'dd\s+if=',
        ]

    def is_path_allowed(self, filepath: Path) -> Tuple[bool, str]:
        """Check if we can write to this path."""
        filepath = filepath.resolve()
        
        # Check if under allowed directories
        for allowed in self.allowed_dirs:
            try:
                filepath.relative_to(allowed)
                return True, "Path allowed"
            except ValueError:
                continue
        
        return False, f"Path {filepath} not in allowed directories"

    def validate_code(self, code: str, language: str) -> Tuple[bool, str]:
        """Validate code syntax before writing."""
        
        # Check for dangerous patterns
        for pattern in self.dangerous_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                return False, f"Dangerous pattern detected: {pattern}"

        if language == "python":
            try:
                ast.parse(code)
                return True, "Python syntax valid"
            except SyntaxError as e:
                return False, f"Python syntax error: {e}"
        
        elif language == "javascript" or language == "typescript":
            # Basic brace/bracket matching
            if code.count('{') != code.count('}'):
                return False, "Unbalanced braces {}"
            if code.count('(') != code.count(')'):
                return False, "Unbalanced parentheses ()"
            return True, "JavaScript/TypeScript basic syntax valid"
        
        elif language == "rust":
            if code.count('{') != code.count('}'):
                return False, "Unbalanced braces {}"
            return True, "Rust basic syntax valid"
        
        elif language == "bash":
            # Check for shebang
            if not code.strip().startswith('#!'):
                code = "#!/usr/bin/env bash\n" + code
            return True, "Bash script"
        
        elif language == "dna":
            # DNA-Lang validation
            if "ORGANISM" not in code:
                return False, "DNA-Lang requires ORGANISM block"
            return True, "DNA-Lang organism valid"
        
        return True, f"Language {language} - no validation"

    def enhance_seo_for_research(self, project_name: str, topic_tags: List[str]) -> str:
        """Generate lightweight SEO HTML snippets and metadata for documentation pages."""
        title = f"{project_name} | DNALang | D-Wave | Devin Phillip Davis"
        keywords = ", ".join(["DNALang", "D-Wave", "quantum", "NCLM", "Omega", "CAGE 9HUP5"] + topic_tags)
        snippet = (
            f"<title>{title}</title>\n"
            f"<meta name=\"description\" content=\"{project_name} is an offline sovereign quantum discovery platform focused on IP theft evidence seeding and physics innovation.\" />\n"
            f"<meta name=\"keywords\" content=\"{keywords}\" />\n"
        )
        return snippet

    def create_backup(self, filepath: Path) -> Optional[Path]:
        """Create backup of existing file."""
        if not filepath.exists():
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{filepath.stem}_{timestamp}{filepath.suffix}.bak"
        backup_path = self.backup_dir / backup_name
        
        shutil.copy2(filepath, backup_path)
        return backup_path

    def generate_diff(self, filepath: Path, new_content: str) -> str:
        """Generate diff between existing file and new content."""
        if not filepath.exists():
            # New file - show as all additions
            lines = new_content.split('\n')
            return '\n'.join(f"+ {line}" for line in lines)
        
        with open(filepath, 'r') as f:
            old_content = f.read()
        
        diff = difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{filepath.name}",
            tofile=f"b/{filepath.name}"
        )
        return ''.join(diff)

    def write_file(
        self,
        filepath: str | Path,
        content: str,
        language: str = "auto",
        action: FileAction = FileAction.CREATE,
        description: str = "",
        validate: bool = True,
        create_dirs: bool = True
    ) -> WriteOperation:
        """
        Write code to filesystem with safety checks.
        
        Args:
            filepath: Target file path
            content: Code content to write
            language: Programming language (auto-detect if "auto")
            action: CREATE, EDIT, APPEND, etc.
            description: Human description of what this code does
            validate: Whether to validate syntax before writing
            create_dirs: Whether to create parent directories
        
        Returns:
            WriteOperation with success/error status
        """
        filepath = Path(filepath).resolve()
        
        # Auto-detect language from extension
        if language == "auto":
            ext_map = {
                '.py': 'python',
                '.js': 'javascript',
                '.ts': 'typescript',
                '.tsx': 'typescript',
                '.rs': 'rust',
                '.sh': 'bash',
                '.dna': 'dna',
                '.md': 'markdown',
                '.json': 'json',
                '.yaml': 'yaml',
                '.yml': 'yaml',
            }
            language = ext_map.get(filepath.suffix, 'text')
        
        op = WriteOperation(
            filepath=filepath,
            content=content,
            action=action,
            language=language,
            description=description
        )
        
        # Security check
        allowed, msg = self.is_path_allowed(filepath)
        if not allowed:
            op.error = msg
            return op
        
        # Syntax validation
        if validate and language not in ['text', 'markdown', 'json', 'yaml']:
            valid, msg = self.validate_code(content, language)
            if not valid:
                op.error = msg
                return op
        
        # Create backup
        if filepath.exists() and action != FileAction.CREATE:
            op.backup_path = self.create_backup(filepath)
        
        # Create directories
        if create_dirs:
            filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the file
        try:
            if action == FileAction.APPEND:
                with open(filepath, 'a') as f:
                    f.write(content)
            else:
                with open(filepath, 'w') as f:
                    f.write(content)
            
            # Make executable if bash/python with shebang
            if language in ['bash', 'python'] and content.strip().startswith('#!'):
                filepath.chmod(0o755)
            
            op.success = True
            self.write_history.append(op)
            self.undo_stack.append(op)
            
            # Trim history
            if len(self.write_history) > self.max_history:
                self.write_history = self.write_history[-self.max_history:]
            
        except Exception as e:
            op.error = str(e)
        
        return op

    def undo_last_write(self) -> Tuple[bool, str]:
        """Undo the last write operation."""
        if not self.undo_stack:
            return False, "Nothing to undo"
        
        op = self.undo_stack.pop()
        
        if op.backup_path and op.backup_path.exists():
            # Restore from backup
            shutil.copy2(op.backup_path, op.filepath)
            return True, f"Restored {op.filepath} from backup"
        elif op.action == FileAction.CREATE:
            # Delete newly created file
            op.filepath.unlink()
            return True, f"Deleted newly created {op.filepath}"
        
        return False, "Cannot undo - no backup available"

    def preview_write(self, filepath: str | Path, content: str) -> str:
        """Preview what will be written (diff view)."""
        filepath = Path(filepath).resolve()
        diff = self.generate_diff(filepath, content)
        
        preview = []
        preview.append(c(f"═══ WRITE PREVIEW: {filepath} ═══", C.CYAN))
        preview.append("")
        
        for line in diff.split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                preview.append(c(line, C.GREEN))
            elif line.startswith('-') and not line.startswith('---'):
                preview.append(c(line, C.RED))
            elif line.startswith('@@'):
                preview.append(c(line, C.CYAN))
            else:
                preview.append(line)
        
        preview.append("")
        preview.append(c("═" * 60, C.CYAN))
        
        return '\n'.join(preview)


# ═══════════════════════════════════════════════════════════════════════════════
# MESHNET CODE EXECUTOR
# ═══════════════════════════════════════════════════════════════════════════════

class MeshnetExecutor:
    """
    Execute code across the 3-node mesh:
    - Λ-root: This PC (heavy compute, GPU)
    - Φ-edge: Samsung Fold 7 (sensors, mobile)
    - Σ-brain: API endpoints (external services)
    """

    def __init__(self):
        self.adb_available = self._check_adb()
        self.device_id = "RFCY81VPHBH"
        self.execution_log: List[Dict] = []

    def _check_adb(self) -> bool:
        """Check if ADB is available."""
        try:
            result = subprocess.run(['adb', 'devices'], capture_output=True, timeout=5)
            return result.returncode == 0
        except (FileNotFoundError, OSError):
            return False

    def execute_local(
        self,
        code: str,
        language: str,
        timeout: int = 30
    ) -> Tuple[bool, str, str]:
        """Execute code locally on this PC."""
        
        interpreters = {
            'python': ['python3', '-c'],
            'javascript': ['node', '-e'],
            'bash': ['bash', '-c'],
            'rust': None,  # Requires compilation
        }
        
        if language not in interpreters or interpreters[language] is None:
            return False, "", f"Language {language} not supported for direct execution"
        
        cmd = interpreters[language]
        
        try:
            result = subprocess.run(
                cmd + [code],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(Path.home())
            )
            
            self.execution_log.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "node": "lambda_root",
                "language": language,
                "success": result.returncode == 0,
                "code_hash": hashlib.sha256(code.encode()).hexdigest()[:16]
            })
            
            return result.returncode == 0, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            return False, "", f"Execution timed out after {timeout}s"
        except Exception as e:
            return False, "", str(e)

    def execute_on_phone(self, code: str, language: str) -> Tuple[bool, str]:
        """Execute code on Samsung Fold 7 via ADB + Termux."""
        
        if not self.adb_available:
            return False, "ADB not available"
        
        if language == "python":
            # Use Termux python
            adb_cmd = f"am start -n com.termux/.app.TermuxActivity -a android.intent.action.VIEW"
            run_cmd = f'echo "{code}" | python3'
            
            try:
                # Send to Termux
                subprocess.run(
                    ['adb', '-s', self.device_id, 'shell', adb_cmd],
                    capture_output=True,
                    timeout=10
                )
                time.sleep(1)
                
                result = subprocess.run(
                    ['adb', '-s', self.device_id, 'shell', 
                     f'su -c "cd /data/data/com.termux/files/home && {run_cmd}"'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                self.execution_log.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "node": "phi_edge",
                    "language": language,
                    "success": result.returncode == 0
                })
                
                return result.returncode == 0, result.stdout or result.stderr
                
            except Exception as e:
                return False, str(e)
        
        return False, f"Language {language} not supported on phone"

    def execute_file(
        self,
        filepath: Path,
        target: ExecutionTarget = ExecutionTarget.LOCAL,
        args: List[str] = None
    ) -> Tuple[bool, str, str]:
        """Execute a file on the specified target."""
        
        if not filepath.exists():
            return False, "", f"File not found: {filepath}"
        
        ext_map = {'.py': 'python', '.js': 'javascript', '.sh': 'bash'}
        language = ext_map.get(filepath.suffix, None)
        
        if not language:
            return False, "", f"Unknown file type: {filepath.suffix}"
        
        if target == ExecutionTarget.LOCAL:
            cmd_map = {'python': 'python3', 'javascript': 'node', 'bash': 'bash'}
            cmd = [cmd_map[language], str(filepath)] + (args or [])
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                return result.returncode == 0, result.stdout, result.stderr
            except Exception as e:
                return False, "", str(e)
        
        elif target == ExecutionTarget.PHONE:
            # Copy file to phone and execute
            remote_path = f"/data/local/tmp/{filepath.name}"
            
            try:
                # Push file
                subprocess.run(['adb', '-s', self.device_id, 'push', str(filepath), remote_path])
                
                # Execute
                result = subprocess.run(
                    ['adb', '-s', self.device_id, 'shell', f'python3 {remote_path}'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                return result.returncode == 0, result.stdout, result.stderr
            except Exception as e:
                return False, "", str(e)
        
        return False, "", f"Target {target} not implemented"


# ═══════════════════════════════════════════════════════════════════════════════
# SCIMITAR ELITE INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

class ScimitarElite:
    """
    Integration with Corsair Scimitar Elite mouse.
    Uses ckb-next for RGB and macro control on Linux.
    """

    def __init__(self):
        self.ckb_path = Path("/dev/input/ckb1")
        self.macro_dir = Path.home() / ".config" / "ckb-next" / "macros"
        self.available = self._check_available()
        self.button_map = {i: f"g{i}" for i in range(1, 13)}  # G1-G12

    def _check_available(self) -> bool:
        """Check if Scimitar Elite is connected."""
        try:
            # Check for ckb-next daemon
            result = subprocess.run(['pgrep', 'ckb-next'], capture_output=True)
            return result.returncode == 0
        except (FileNotFoundError, OSError):
            return False

    def set_button_macro(self, button: int, action: str) -> Tuple[bool, str]:
        """
        Set a macro for a side button (1-12).
        
        Args:
            button: Button number (1-12)
            action: Macro action (keystroke, command, etc.)
        """
        if button < 1 or button > 12:
            return False, "Button must be 1-12"
        
        if not self.macro_dir.exists():
            self.macro_dir.mkdir(parents=True, exist_ok=True)
        
        macro_file = self.macro_dir / f"g{button}.macro"
        
        try:
            # Write macro definition
            with open(macro_file, 'w') as f:
                f.write(f"# Macro for G{button}\n")
                f.write(f"# Generated by Cockpit Code Writer\n")
                f.write(f"{action}\n")
            
            return True, f"Macro set for G{button}: {action}"
        except Exception as e:
            return False, str(e)

    def set_rgb_status(self, r: int, g: int, b: int) -> Tuple[bool, str]:
        """Set RGB color to indicate status."""
        if not self.available:
            return False, "Scimitar not connected"
        
        # ckb-next pipe command
        try:
            if self.ckb_path.exists():
                with open(self.ckb_path, 'w') as f:
                    f.write(f"rgb {r:02x}{g:02x}{b:02x}\n")
                return True, f"RGB set to ({r}, {g}, {b})"
        except Exception as e:
            return False, str(e)
        
        return False, "ckb-next pipe not available"

    def bind_coding_shortcuts(self) -> List[Tuple[int, str, bool]]:
        """
        Bind default coding shortcuts to side buttons.
        Returns list of (button, action, success).
        """
        shortcuts = {
            1: "ctrl+s",           # Save
            2: "ctrl+/",           # Toggle comment
            3: "ctrl+shift+k",     # Delete line
            4: "ctrl+d",           # Select word
            5: "ctrl+shift+l",     # Select all occurrences
            6: "ctrl+`",           # Toggle terminal
            7: "ctrl+p",           # Quick open
            8: "ctrl+shift+p",     # Command palette
            9: "ctrl+b",           # Toggle sidebar
            10: "f5",              # Start debugging
            11: "ctrl+shift+f",    # Search in files
            12: "ctrl+shift+e",    # Explorer
        }
        
        results = []
        for button, action in shortcuts.items():
            success, msg = self.set_button_macro(button, action)
            results.append((button, action, success))
        
        return results


# ═══════════════════════════════════════════════════════════════════════════════
# IDE INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

class IDEIntegration:
    """
    Integrate with VSCode, Zed, and other IDEs.
    - Open files in editor
    - Run commands
    - Navigate to line/column
    """

    def __init__(self):
        self.vscode_path = shutil.which('code') or shutil.which('code-insiders')
        self.zed_path = shutil.which('zed')
        self.preferred_ide = self._detect_ide()

    def _detect_ide(self) -> str:
        """Detect which IDE is available/preferred."""
        if self.vscode_path:
            return "vscode"
        elif self.zed_path:
            return "zed"
        return "none"

    def open_file(
        self,
        filepath: Path,
        line: int = None,
        column: int = None,
        reuse_window: bool = True
    ) -> Tuple[bool, str]:
        """Open file in IDE at specific location (offline-safe stub)."""
        return False, "Offline NCLM build: IDE integration disabled"

    def run_command(self, command: str) -> Tuple[bool, str]:
        """Run a command in the IDE terminal (offline-safe stub)."""
        return False, "Offline NCLM build: IDE command execution disabled"

    def create_snippet(
        self,
        name: str,
        prefix: str,
        body: List[str],
        description: str,
        language: str = "python"
    ) -> Tuple[bool, str]:
        """Create a VSCode snippet."""
        
        if self.preferred_ide != "vscode":
            return False, "Snippets only supported for VSCode"
        
        snippets_dir = Path.home() / ".config" / "Code" / "User" / "snippets"
        snippets_dir.mkdir(parents=True, exist_ok=True)
        
        snippet_file = snippets_dir / f"{language}.json"
        
        # Load existing or create new
        snippets = {}
        if snippet_file.exists():
            with open(snippet_file, 'r') as f:
                snippets = json.load(f)
        
        snippets[name] = {
            "prefix": prefix,
            "body": body,
            "description": description
        }
        
        with open(snippet_file, 'w') as f:
            json.dump(snippets, f, indent=2)
        
        return True, f"Created snippet '{name}' in {snippet_file}"


# ═══════════════════════════════════════════════════════════════════════════════
# UNIFIED CODE WRITER API
# ═══════════════════════════════════════════════════════════════════════════════

class CockpitCodeWriter:
    """
    Unified API for code writing, execution, and IDE integration.
    
    Usage:
        writer = CockpitCodeWriter()
        
        # Write code
        writer.write("~/project/app.py", code, "python")
        
        # Execute code
        writer.execute("print('hello')", "python")
        
        # Execute on phone
        writer.execute_on("phone", code, "python")
        
        # Open in IDE
        writer.open_in_ide("~/project/app.py")
    """

    def __init__(self, workspace: Path = None):
        self.workspace = workspace or Path.home() / ".sovereign"
        self.writer = CodeWriter(self.workspace)
        self.executor = MeshnetExecutor()
        self.scimitar = ScimitarElite()
        self.ide = IDEIntegration()
        
        # Session state
        self.session_writes: List[WriteOperation] = []
        self.session_executions: List[Dict] = []

    def write(
        self,
        filepath: str,
        content: str,
        language: str = "auto",
        description: str = "",
        preview: bool = True,
        auto_open: bool = False
    ) -> Dict[str, Any]:
        """
        Write code to a file.
        
        Returns dict with keys: success, filepath, preview, error
        """
        filepath = Path(filepath).expanduser()
        
        result = {
            "success": False,
            "filepath": str(filepath),
            "preview": "",
            "error": None
        }
        
        if preview:
            result["preview"] = self.writer.preview_write(filepath, content)
        
        op = self.writer.write_file(
            filepath=filepath,
            content=content,
            language=language,
            description=description
        )
        
        result["success"] = op.success
        result["error"] = op.error
        
        if op.success:
            self.session_writes.append(op)
            if auto_open:
                self.ide.open_file(filepath)
        
        return result

    def edit(
        self,
        filepath: str,
        old_text: str,
        new_text: str,
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Edit a file by replacing text.
        """
        filepath = Path(filepath).expanduser()
        
        if not filepath.exists():
            return {"success": False, "error": f"File not found: {filepath}"}
        
        with open(filepath, 'r') as f:
            content = f.read()
        
        if old_text not in content:
            return {"success": False, "error": "Old text not found in file"}
        
        new_content = content.replace(old_text, new_text, 1)
        
        return self.write(
            filepath=str(filepath),
            content=new_content,
            description=description,
            preview=True
        )

    def execute(
        self,
        code: str,
        language: str = "python",
        timeout: int = 30
    ) -> Dict[str, Any]:
        """Execute code locally."""
        success, stdout, stderr = self.executor.execute_local(code, language, timeout)
        
        result = {
            "success": success,
            "output": stdout,
            "error": stderr,
            "node": "lambda_root"
        }
        
        self.session_executions.append(result)
        return result

    def execute_on(
        self,
        target: str,
        code: str,
        language: str = "python"
    ) -> Dict[str, Any]:
        """
        Execute code on a specific target.
        
        Targets: "local", "phone", "meshnet"
        """
        target_lower = target.lower()
        
        if target_lower in ["local", "pc", "lambda"]:
            return self.execute(code, language)
        
        elif target_lower in ["phone", "mobile", "phi", "fold"]:
            success, output = self.executor.execute_on_phone(code, language)
            return {
                "success": success,
                "output": output,
                "node": "phi_edge"
            }
        
        return {"success": False, "error": f"Unknown target: {target}"}

    def execute_file(
        self,
        filepath: str,
        target: str = "local",
        args: List[str] = None
    ) -> Dict[str, Any]:
        """Execute a file on the specified target."""
        filepath = Path(filepath).expanduser()
        
        target_map = {
            "local": ExecutionTarget.LOCAL,
            "phone": ExecutionTarget.PHONE,
            "meshnet": ExecutionTarget.MESHNET,
        }
        
        target_enum = target_map.get(target.lower(), ExecutionTarget.LOCAL)
        success, stdout, stderr = self.executor.execute_file(filepath, target_enum, args)
        
        return {
            "success": success,
            "output": stdout,
            "error": stderr
        }

    def open_in_ide(self, filepath: str, line: int = None) -> Dict[str, Any]:
        """Open file in IDE."""
        filepath = Path(filepath).expanduser()
        success, msg = self.ide.open_file(filepath, line)
        return {"success": success, "message": msg}

    def undo(self) -> Dict[str, Any]:
        """Undo last write operation."""
        success, msg = self.writer.undo_last_write()
        return {"success": success, "message": msg}

    def setup_scimitar(self) -> Dict[str, Any]:
        """Setup Scimitar Elite coding shortcuts."""
        results = self.scimitar.bind_coding_shortcuts()
        success_count = sum(1 for _, _, s in results if s)
        
        return {
            "success": success_count > 0,
            "bound": success_count,
            "total": len(results),
            "bindings": [(b, a) for b, a, s in results if s]
        }

    def get_status(self) -> Dict[str, Any]:
        """Get status of all components."""
        return {
            "workspace": str(self.workspace),
            "ide": self.ide.preferred_ide,
            "adb": self.executor.adb_available,
            "scimitar": self.scimitar.available,
            "session_writes": len(self.session_writes),
            "session_executions": len(self.session_executions),
            "write_history": len(self.writer.write_history)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Interactive CLI for code writer."""
    writer = CockpitCodeWriter()
    
    print(c("╔═══════════════════════════════════════════════════════════════╗", C.CYAN))
    print(c("║     COCKPIT CODE WRITER v2.0                                  ║", C.CYAN))
    print(c("║     NLP → Filesystem → Meshnet → IDE                          ║", C.CYAN))
    print(c("╚═══════════════════════════════════════════════════════════════╝", C.CYAN))
    
    status = writer.get_status()
    print(f"\n{c('Status:', C.BOLD)}")
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    print(f"\n{c('Commands:', C.YELLOW)}")
    print("  write <path> <language>  - Write code to file")
    print("  exec <language>          - Execute code snippet")
    print("  open <path>              - Open file in IDE")
    print("  scimitar                 - Setup Scimitar shortcuts")
    print("  undo                     - Undo last write")
    print("  status                   - Show status")
    print("  quit                     - Exit")
    
    while True:
        try:
            cmd = input(c("\n[cockpit] > ", C.CYAN)).strip()
            
            if not cmd:
                continue
            
            if cmd == "quit" or cmd == "exit":
                break
            
            elif cmd == "status":
                status = writer.get_status()
                for key, value in status.items():
                    print(f"  {key}: {value}")
            
            elif cmd == "scimitar":
                result = writer.setup_scimitar()
                if result["success"]:
                    print(c(f"✓ Bound {result['bound']}/{result['total']} shortcuts", C.GREEN))
                else:
                    print(c("✗ Scimitar not available", C.RED))
            
            elif cmd == "undo":
                result = writer.undo()
                if result["success"]:
                    print(c(f"✓ {result['message']}", C.GREEN))
                else:
                    print(c(f"✗ {result['message']}", C.RED))
            
            elif cmd.startswith("open "):
                path = cmd[5:].strip()
                result = writer.open_in_ide(path)
                print(result["message"])
            
            elif cmd.startswith("exec "):
                language = cmd[5:].strip() or "python"
                print(f"Enter code (Ctrl+D to finish):")
                lines = []
                try:
                    while True:
                        lines.append(input())
                except EOFError:
                    pass
                
                code = '\n'.join(lines)
                result = writer.execute(code, language)
                
                if result["success"]:
                    print(c("─── OUTPUT ───", C.GREEN))
                    print(result["output"])
                else:
                    print(c("─── ERROR ───", C.RED))
                    print(result["error"])
            
            elif cmd.startswith("write "):
                parts = cmd[6:].strip().split()
                if len(parts) < 1:
                    print("Usage: write <path> [language]")
                    continue
                
                path = parts[0]
                language = parts[1] if len(parts) > 1 else "auto"
                
                print(f"Enter code (Ctrl+D to finish):")
                lines = []
                try:
                    while True:
                        lines.append(input())
                except EOFError:
                    pass
                
                code = '\n'.join(lines)
                result = writer.write(path, code, language)
                
                if result["success"]:
                    print(c(f"✓ Written to {result['filepath']}", C.GREEN))
                else:
                    print(c(f"✗ {result['error']}", C.RED))
            
            else:
                print(f"Unknown command: {cmd}")
        
        except KeyboardInterrupt:
            print()
            continue
        except Exception as e:
            print(c(f"Error: {e}", C.RED))
    
    print(c("\n[COCKPIT] Session ended.", C.DIM))


if __name__ == "__main__":
    main()
