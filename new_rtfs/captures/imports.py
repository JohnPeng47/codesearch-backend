from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Dict, List, Any, Protocol
from pathlib import Path


@dataclass
class TSCaptureInfo:
    """Represents the location information of an import statement in source code."""
    start_line: int
    end_line: int
    start_column: int
    end_column: int
    offset: int
    length: int


@dataclass
class ImportSpecifier:
    """Represents a specific imported item/symbol from a module."""
    original_name: str
    local_name: str
    is_default: bool
    location: Optional[TSCaptureInfo] = None

    @property
    def is_aliased(self) -> bool:
        """Check if the import uses an alias."""
        return self.original_name != self.local_name


@dataclass
class ImportSource:
    """Represents the source/target of the import."""
    raw: str
    resolved_path: Optional[Path] = None
    is_relative: bool = False
    is_builtin: bool = False
    location: Optional[TSCaptureInfo] = None

    def resolve(self) -> Optional[Path]:
        """Attempt to resolve the import path to an absolute path."""
        if self.resolved_path:
            return self.resolved_path
        # Implementation would depend on language-specific resolution rules
        return None


class ImportKind(Enum):
    """Enumeration of possible import types."""
    STATIC = auto()
    DYNAMIC = auto()
    NAMESPACE = auto()
    WILDCARD = auto()


@dataclass
class ImportDeclaration(ABC):
    """Abstract base class for import declarations across languages."""
    kind: ImportKind
    specifiers: List[ImportSpecifier]
    source: ImportSource
    location: SourceLocation
    metadata: Dict[str, Any]

    @abstractmethod
    def validate(self) -> bool:
        """Validate the import declaration."""
        pass

    @abstractmethod
    def to_source(self) -> str:
        """Convert the import declaration back to source code."""
        pass


class ImportAnalyzer(Protocol):
    """Protocol defining the interface for language-specific import analyzers."""
    
    def parse_imports(self, source_code: str) -> List[ImportDeclaration]:
        """Parse import statements from source code."""
        ...

    def validate_import(self, import_decl: ImportDeclaration) -> bool:
        """Validate an import declaration."""
        ...

    async def resolve_import_path(self, import_decl: ImportDeclaration) -> Optional[Path]:
        """Resolve import paths to absolute paths."""
        ...



class ImportAnalyzerFactory:
    """Factory for creating language-specific import analyzers."""
    
    _analyzers: Dict[str, type[ImportAnalyzer]] = {
        'python': PythonImportAnalyzer
    }

    @classmethod
    def register_analyzer(cls, language: str, analyzer_class: type[ImportAnalyzer]) -> None:
        """Register a new language-specific analyzer."""
        cls._analyzers[language.lower()] = analyzer_class

    @classmethod
    def create_analyzer(cls, language: str) -> ImportAnalyzer:
        """Create an analyzer instance for the specified language."""
        analyzer_class = cls._analyzers.get(language.lower())
        if not analyzer_class:
            raise ValueError(f"No analyzer registered for language: {language}")
        return analyzer_class()