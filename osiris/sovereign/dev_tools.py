"""
Developer Tools — file system, search, code analysis.
"""

import os
import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FileSearchResult:
    path: str
    line_number: Optional[int] = None
    context: Optional[str] = None


@dataclass
class CodeAnalysisResult:
    file_path: str
    issues: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    suggestions: List[str]


class DeveloperTools:
    """File system, search, and code analysis tools."""

    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = workspace_root or os.getcwd()

    def search_in_files(self, query: str, directory: str = ".",
                        file_pattern: str = "*.py") -> List[FileSearchResult]:
        results: List[FileSearchResult] = []
        root = os.path.join(self.workspace_root, directory)
        pattern = re.compile(query, re.IGNORECASE)
        for dirpath, _, files in os.walk(root):
            for f in files:
                if not f.endswith(file_pattern.replace("*", "")):
                    continue
                fp = os.path.join(dirpath, f)
                try:
                    with open(fp, "r", encoding="utf-8") as fh:
                        for ln, line in enumerate(fh, 1):
                            if pattern.search(line):
                                results.append(FileSearchResult(
                                    path=os.path.relpath(fp, self.workspace_root),
                                    line_number=ln, context=line.strip(),
                                ))
                except Exception:
                    pass
        return results

    def analyze_code(self, file_path: str) -> CodeAnalysisResult:
        fp = os.path.join(self.workspace_root, file_path)
        try:
            with open(fp, "r") as f:
                content = f.read()
            lines = content.split("\n")
            loc = len([l for l in lines if l.strip() and not l.strip().startswith("#")])
            functions = len(re.findall(r"^\s*def ", content, re.MULTILINE))
            classes = len(re.findall(r"^\s*class ", content, re.MULTILINE))
            return CodeAnalysisResult(
                file_path=file_path, issues=[],
                metrics={"loc": loc, "functions": functions, "classes": classes},
                suggestions=[],
            )
        except Exception as e:
            return CodeAnalysisResult(
                file_path=file_path,
                issues=[{"type": "error", "message": str(e)}],
                metrics={}, suggestions=[],
            )
