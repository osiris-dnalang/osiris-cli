"""
Developer Tools - File System, Git, Search, Analysis
Makes the SDK a complete development assistant
"""

import os
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import re


@dataclass
class FileSearchResult:
    """Result of file search"""
    path: str
    line_number: Optional[int] = None
    context: Optional[str] = None
    match_type: str = "exact"


@dataclass
class CodeAnalysisResult:
    """Result of code analysis"""
    file_path: str
    issues: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    suggestions: List[str]


class DeveloperTools:
    """
    Advanced developer assistance tools
    
    Features:
    - File system operations (read, write, search)
    - Git operations (status, diff, commit)
    - Code search (grep, semantic search)
    - Code analysis (complexity, quality)
    - Refactoring assistance
    - Documentation generation
    """
    
    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = workspace_root or os.getcwd()
    
    # File System Operations
    
    async def read_file(self, path: str) -> str:
        """Read file contents"""
        full_path = self._resolve_path(path)
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    async def write_file(self, path: str, content: str) -> bool:
        """Write content to file"""
        full_path = self._resolve_path(path)
        try:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"Error writing file: {str(e)}")
            return False
    
    async def list_files(
        self,
        directory: str = ".",
        pattern: Optional[str] = None,
        recursive: bool = False
    ) -> List[str]:
        """List files in directory"""
        full_dir = self._resolve_path(directory)
        
        try:
            if recursive:
                files = []
                for root, dirs, filenames in os.walk(full_dir):
                    for filename in filenames:
                        file_path = os.path.join(root, filename)
                        if pattern is None or self._matches_pattern(filename, pattern):
                            files.append(os.path.relpath(file_path, self.workspace_root))
                return files
            else:
                files = os.listdir(full_dir)
                if pattern:
                    files = [f for f in files if self._matches_pattern(f, pattern)]
                return files
        except Exception as e:
            print(f"Error listing files: {str(e)}")
            return []
    
    async def search_in_files(
        self,
        query: str,
        directory: str = ".",
        file_pattern: str = "*.py",
        case_sensitive: bool = False
    ) -> List[FileSearchResult]:
        """Search for text in files (like grep)"""
        results = []
        full_dir = self._resolve_path(directory)
        
        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = re.compile(query, flags)
        
        for root, dirs, files in os.walk(full_dir):
            for file in files:
                if self._matches_pattern(file, file_pattern):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            for line_num, line in enumerate(f, 1):
                                if pattern.search(line):
                                    results.append(FileSearchResult(
                                        path=os.path.relpath(file_path, self.workspace_root),
                                        line_number=line_num,
                                        context=line.strip(),
                                        match_type="regex"
                                    ))
                    except Exception:
                        pass  # Skip files that can't be read
        
        return results
    
    # Git Operations
    
    async def git_status(self) -> str:
        """Get git status"""
        return self._run_command("git status --short")
    
    async def git_diff(self, file_path: Optional[str] = None) -> str:
        """Get git diff"""
        cmd = "git diff"
        if file_path:
            cmd += f" {file_path}"
        return self._run_command(cmd)
    
    async def git_log(self, max_count: int = 10) -> str:
        """Get git log"""
        return self._run_command(f"git log --oneline -n {max_count}")
    
    async def git_commit(self, message: str, files: Optional[List[str]] = None) -> bool:
        """Commit changes"""
        try:
            if files:
                for file in files:
                    self._run_command(f"git add {file}")
            else:
                self._run_command("git add -A")
            
            self._run_command(f'git commit -m "{message}"')
            return True
        except Exception as e:
            print(f"Error committing: {str(e)}")
            return False
    
    # Code Analysis
    
    async def analyze_code(self, file_path: str) -> CodeAnalysisResult:
        """Analyze code quality and complexity"""
        full_path = self._resolve_path(file_path)
        
        try:
            content = await self.read_file(file_path)
            
            # Basic analysis
            issues = self._detect_code_issues(content)
            metrics = self._calculate_metrics(content)
            suggestions = self._generate_suggestions(issues, metrics)
            
            return CodeAnalysisResult(
                file_path=file_path,
                issues=issues,
                metrics=metrics,
                suggestions=suggestions
            )
        except Exception as e:
            return CodeAnalysisResult(
                file_path=file_path,
                issues=[{"type": "error", "message": str(e)}],
                metrics={},
                suggestions=[]
            )
    
    async def find_functions(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract all functions from file"""
        content = await self.read_file(file_path)
        functions = []
        
        # Simple regex-based extraction (in production, use AST)
        pattern = r'def\s+(\w+)\s*\(([^)]*)\):'
        for match in re.finditer(pattern, content):
            functions.append({
                "name": match.group(1),
                "params": match.group(2).strip(),
                "line": content[:match.start()].count('\n') + 1
            })
        
        return functions
    
    async def find_classes(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract all classes from file"""
        content = await self.read_file(file_path)
        classes = []
        
        pattern = r'class\s+(\w+)(?:\(([^)]*)\))?:'
        for match in re.finditer(pattern, content):
            classes.append({
                "name": match.group(1),
                "bases": match.group(2).strip() if match.group(2) else "",
                "line": content[:match.start()].count('\n') + 1
            })
        
        return classes
    
    # Project Operations
    
    async def get_project_structure(self) -> Dict[str, Any]:
        """Get overview of project structure"""
        structure = {
            "root": self.workspace_root,
            "files": {
                "total": 0,
                "python": 0,
                "javascript": 0,
                "other": 0
            },
            "directories": [],
            "lines_of_code": 0
        }
        
        for root, dirs, files in os.walk(self.workspace_root):
            structure["directories"].extend(dirs)
            
            for file in files:
                structure["files"]["total"] += 1
                
                if file.endswith('.py'):
                    structure["files"]["python"] += 1
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r') as f:
                            structure["lines_of_code"] += len(f.readlines())
                    except (OSError, UnicodeDecodeError):
                        pass
                elif file.endswith(('.js', '.ts', '.jsx', '.tsx')):
                    structure["files"]["javascript"] += 1
                else:
                    structure["files"]["other"] += 1
        
        return structure
    
    async def find_dependencies(self, file_path: str) -> List[str]:
        """Find imports/dependencies in file"""
        content = await self.read_file(file_path)
        dependencies = []
        
        # Python imports
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('import ') or line.startswith('from '):
                dependencies.append(line)
        
        return dependencies
    
    # Helper Methods
    
    def _resolve_path(self, path: str) -> str:
        """Resolve path relative to workspace"""
        if os.path.isabs(path):
            return path
        return os.path.join(self.workspace_root, path)
    
    def _matches_pattern(self, filename: str, pattern: str) -> bool:
        """Check if filename matches pattern"""
        if pattern == "*":
            return True
        if pattern.startswith("*."):
            ext = pattern[2:]
            return filename.endswith(f".{ext}")
        return filename == pattern
    
    def _run_command(self, cmd: str) -> str:
        """Run shell command"""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout if result.returncode == 0 else result.stderr
        except Exception as e:
            return f"Error: {str(e)}"
    
    def _detect_code_issues(self, content: str) -> List[Dict[str, Any]]:
        """Detect common code issues"""
        issues = []
        
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            # Check line length
            if len(line) > 100:
                issues.append({
                    "type": "style",
                    "line": i,
                    "message": "Line too long (>100 characters)"
                })
            
            # Check for TODO comments
            if 'TODO' in line or 'FIXME' in line:
                issues.append({
                    "type": "todo",
                    "line": i,
                    "message": "TODO/FIXME found"
                })
        
        return issues
    
    def _calculate_metrics(self, content: str) -> Dict[str, Any]:
        """Calculate code metrics"""
        lines = content.split('\n')
        
        return {
            "total_lines": len(lines),
            "code_lines": len([l for l in lines if l.strip() and not l.strip().startswith('#')]),
            "comment_lines": len([l for l in lines if l.strip().startswith('#')]),
            "blank_lines": len([l for l in lines if not l.strip()]),
            "functions": len(re.findall(r'def\s+\w+', content)),
            "classes": len(re.findall(r'class\s+\w+', content)),
        }
    
    def _generate_suggestions(self, issues: List[Dict], metrics: Dict) -> List[str]:
        """Generate improvement suggestions"""
        suggestions = []
        
        if metrics.get('code_lines', 0) > 500:
            suggestions.append("Consider splitting into smaller modules")
        
        if metrics.get('comment_lines', 0) < metrics.get('code_lines', 1) * 0.1:
            suggestions.append("Add more comments/documentation")
        
        if len([i for i in issues if i['type'] == 'style']) > 5:
            suggestions.append("Run code formatter (black, autopep8)")
        
        return suggestions
