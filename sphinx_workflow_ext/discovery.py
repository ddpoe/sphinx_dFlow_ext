"""
Workflow auto-discovery system.

Scans directories for Python files with workflow markers and builds
a registry of available workflows and their tiers.

Key Markers Detected:
- # WORKFLOWS: tier1, tier2, tier3  (in module docstring)
- # DOCUMENT_WORKFLOW: tier1, tier2  (in function docstring)
- # WORKFLOW_EXCLUDE: tier1  (above function)
"""

import fnmatch
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredWorkflow:
    """Represents a discovered workflow module with its tiers."""
    
    module_path: Path
    """Absolute path to the Python module."""
    
    module_name: str
    """Human-readable module name (e.g., 'model_selection')."""
    
    package_name: Optional[str]
    """Package name if part of a package (e.g., 'elastic_net_modules')."""
    
    declared_tiers: List[str]
    """List of tier names from # WORKFLOWS: declaration."""
    
    entry_points: Dict[str, str] = field(default_factory=dict)
    """Maps tier name -> entry function name (from # DOCUMENT_WORKFLOW)."""
    
    docstring: Optional[str] = None
    """First line of module docstring (for descriptions)."""
    
    line_count: int = 0
    """Number of lines in the module (for complexity indicator)."""
    
    @property
    def display_name(self) -> str:
        """Get display name for UI (package.module or just module)."""
        if self.package_name:
            return f"{self.package_name}.{self.module_name}"
        return self.module_name
    
    @property
    def has_tiers(self) -> bool:
        """Check if module has multi-tier workflow."""
        return len(self.declared_tiers) > 0


@dataclass
class DiscoveryResult:
    """Result of workflow discovery across directories."""
    
    workflows: Dict[str, DiscoveredWorkflow] = field(default_factory=dict)
    """Maps module path (str) -> DiscoveredWorkflow."""
    
    errors: List[str] = field(default_factory=list)
    """List of errors encountered during discovery."""
    
    skipped: List[Tuple[str, str]] = field(default_factory=list)
    """List of (path, reason) for skipped files."""
    
    @property
    def modules_by_package(self) -> Dict[str, List[DiscoveredWorkflow]]:
        """Group discovered workflows by package name."""
        result: Dict[str, List[DiscoveredWorkflow]] = {}
        for workflow in self.workflows.values():
            package = workflow.package_name or "_root"
            if package not in result:
                result[package] = []
            result[package].append(workflow)
        
        # Sort modules within each package
        for modules in result.values():
            modules.sort(key=lambda w: w.module_name)
        
        return result
    
    def get_all_tiers(self) -> Set[str]:
        """Get set of all unique tier names across all workflows."""
        tiers = set()
        for workflow in self.workflows.values():
            tiers.update(workflow.declared_tiers)
        return tiers


class WorkflowDiscovery:
    """
    Auto-discovery system for workflow modules.
    
    Scans directories for Python files containing workflow markers
    and builds a registry of available workflows.
    
    Example usage:
        discovery = WorkflowDiscovery()
        result = discovery.discover(['protocols/', 'modules/'])
        
        for package, modules in result.modules_by_package.items():
            print(f"Package: {package}")
            for module in modules:
                print(f"  - {module.module_name}: {module.declared_tiers}")
    """
    
    # Regex patterns for marker detection
    WORKFLOWS_PATTERN = re.compile(
        r'^\s*#\s*WORKFLOWS:\s*(.+)$',
        re.MULTILINE | re.IGNORECASE
    )
    
    DOCUMENT_WORKFLOW_PATTERN = re.compile(
        r'^\s*#\s*DOCUMENT_WORKFLOW:\s*(.+)$',
        re.MULTILINE
    )
    
    # Pattern to extract docstring first line
    DOCSTRING_PATTERN = re.compile(
        r'^(?:"""|\'\'\')(.*?)(?:"""|\'\'\')|("""|\'\'\')(.+?)$',
        re.MULTILINE | re.DOTALL
    )
    
    def __init__(
        self,
        base_path: Optional[Path] = None,
        exclude_patterns: Optional[List[str]] = None,
        include_patterns: Optional[List[str]] = None,
        verbose: bool = False
    ):
        """
        Initialize discovery system.
        
        Args:
            base_path: Base directory for resolving relative paths.
                       Defaults to current working directory.
            exclude_patterns: Glob patterns for files/dirs to exclude.
                              Defaults to ['test_*', '_*', '.*']
            include_patterns: Glob patterns for files to include.
                              Defaults to ['*.py']
            verbose: Enable verbose logging.
        """
        self.base_path = base_path or Path.cwd()
        self.exclude_patterns = exclude_patterns or ['test_*', '_*', '.*', '*_test.py', 'conftest.py']
        self.include_patterns = include_patterns or ['*.py']
        self.verbose = verbose
    
    def discover(
        self,
        search_paths: List[str],
        recursive: bool = True
    ) -> DiscoveryResult:
        """
        Discover all workflow modules in given paths.
        
        Args:
            search_paths: List of directories to scan (relative to base_path).
            recursive: Whether to search subdirectories.
        
        Returns:
            DiscoveryResult with discovered workflows and any errors.
        """
        result = DiscoveryResult()
        
        for search_path in search_paths:
            path = self._resolve_path(search_path)
            
            if not path.exists():
                result.errors.append(f"Search path not found: {search_path}")
                continue
            
            if path.is_file():
                # Single file
                self._process_file(path, result)
            else:
                # Directory
                self._scan_directory(path, result, recursive)
        
        return result
    
    def discover_in_directory(
        self,
        directory: Path,
        recursive: bool = True
    ) -> DiscoveryResult:
        """
        Discover all workflow modules in a single directory.
        
        Args:
            directory: Directory to scan.
            recursive: Whether to search subdirectories.
        
        Returns:
            DiscoveryResult with discovered workflows.
        """
        result = DiscoveryResult()
        self._scan_directory(directory, result, recursive)
        return result
    
    def _resolve_path(self, path: str) -> Path:
        """Resolve path relative to base_path."""
        p = Path(path)
        if p.is_absolute():
            return p
        return self.base_path / p
    
    def _should_exclude(self, path: Path) -> bool:
        """Check if path should be excluded based on patterns."""
        name = path.name
        
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(name, pattern):
                return True
        
        return False
    
    def _should_include(self, path: Path) -> bool:
        """Check if file should be included based on patterns."""
        name = path.name
        
        for pattern in self.include_patterns:
            if fnmatch.fnmatch(name, pattern):
                return True
        
        return False
    
    def _scan_directory(
        self,
        directory: Path,
        result: DiscoveryResult,
        recursive: bool
    ) -> None:
        """Scan a directory for workflow modules."""
        if self._should_exclude(directory):
            result.skipped.append((str(directory), "Excluded by pattern"))
            return
        
        try:
            for entry in directory.iterdir():
                if entry.is_dir():
                    if recursive and not self._should_exclude(entry):
                        self._scan_directory(entry, result, recursive)
                elif entry.is_file() and self._should_include(entry):
                    if not self._should_exclude(entry):
                        self._process_file(entry, result)
                    else:
                        result.skipped.append((str(entry), "Excluded by pattern"))
        except PermissionError as e:
            result.errors.append(f"Permission denied: {directory}")
    
    def _process_file(
        self,
        file_path: Path,
        result: DiscoveryResult
    ) -> None:
        """
        Process a single Python file, extracting workflow info if present.
        
        Args:
            file_path: Path to Python file.
            result: DiscoveryResult to populate.
        """
        try:
            source = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            try:
                source = file_path.read_text(encoding='latin-1')
            except Exception as e:
                result.errors.append(f"Could not read {file_path}: {e}")
                return
        except Exception as e:
            result.errors.append(f"Could not read {file_path}: {e}")
            return
        
        # Check for WORKFLOWS declaration
        workflows_match = self.WORKFLOWS_PATTERN.search(source[:2000])  # Search in first 2000 chars
        
        if not workflows_match:
            # Also check for DOCUMENT_WORKFLOW markers (single-tier mode)
            doc_workflow_match = self.DOCUMENT_WORKFLOW_PATTERN.search(source)
            if not doc_workflow_match:
                result.skipped.append((str(file_path), "No workflow markers"))
                return
            # Single-tier mode: treat as having one tier named 'default' or extract from marker
            declared_tiers = self._extract_single_tier_names(source)
        else:
            # Multi-tier mode: extract tier names from WORKFLOWS declaration
            tiers_text = workflows_match.group(1).strip()
            declared_tiers = [t.strip() for t in tiers_text.split(',') if t.strip()]
        
        if not declared_tiers:
            result.skipped.append((str(file_path), "No valid tier names"))
            return
        
        # Extract additional info
        entry_points = self._extract_entry_points(source)
        docstring = self._extract_docstring_summary(source)
        line_count = source.count('\n') + 1
        
        # Determine module and package names
        module_name = file_path.stem
        package_name = self._detect_package_name(file_path)
        
        # Create workflow record
        workflow = DiscoveredWorkflow(
            module_path=file_path,
            module_name=module_name,
            package_name=package_name,
            declared_tiers=declared_tiers,
            entry_points=entry_points,
            docstring=docstring,
            line_count=line_count
        )
        
        result.workflows[str(file_path)] = workflow
        
        if self.verbose:
            logger.info(f"Discovered: {workflow.display_name} with tiers: {declared_tiers}")
    
    def _extract_single_tier_names(self, source: str) -> List[str]:
        """Extract tier names from DOCUMENT_WORKFLOW markers (single-tier mode)."""
        tiers = set()
        
        for match in self.DOCUMENT_WORKFLOW_PATTERN.finditer(source):
            names_text = match.group(1).strip()
            for name in names_text.split(','):
                name = name.strip()
                if name:
                    tiers.add(name)
        
        return sorted(list(tiers)) if tiers else ['default']
    
    def _extract_entry_points(self, source: str) -> Dict[str, str]:
        """
        Extract mapping of tier name -> entry function name.
        
        Parses # DOCUMENT_WORKFLOW: markers and associates them
        with the next function definition.
        """
        entry_points: Dict[str, str] = {}
        
        # Pattern to find function after marker
        function_pattern = re.compile(r'def\s+(\w+)\s*\(')
        
        for match in self.DOCUMENT_WORKFLOW_PATTERN.finditer(source):
            tiers_text = match.group(1).strip()
            tier_names = [t.strip() for t in tiers_text.split(',') if t.strip()]
            
            # Find next function definition
            remaining = source[match.end():]
            func_match = function_pattern.search(remaining)
            
            if func_match:
                function_name = func_match.group(1)
                for tier in tier_names:
                    if tier not in entry_points:
                        entry_points[tier] = function_name
        
        return entry_points
    
    def _extract_docstring_summary(self, source: str) -> Optional[str]:
        """Extract first line of module docstring."""
        # Check for docstring at start of file
        lines = source.lstrip().split('\n')
        if not lines:
            return None
        
        first_line = lines[0].strip()
        
        # Check for triple quote start
        for quote in ['"""', "'''"]:
            if first_line.startswith(quote):
                # Single line docstring?
                if first_line.endswith(quote) and len(first_line) > 6:
                    return first_line[3:-3].strip()
                
                # Multi-line docstring
                content_start = first_line[3:].strip()
                if content_start:
                    return content_start
                
                # Content on next line
                if len(lines) > 1:
                    return lines[1].strip()
        
        return None
    
    def _detect_package_name(self, file_path: Path) -> Optional[str]:
        """
        Detect package name from file location.
        
        Looks for __init__.py in parent directories to determine package.
        """
        parent = file_path.parent
        
        # Check if parent is a package (has __init__.py)
        init_file = parent / '__init__.py'
        
        if init_file.exists():
            package_name = parent.name
            
            # Check for nested packages
            grandparent = parent.parent
            if (grandparent / '__init__.py').exists():
                return f"{grandparent.name}.{package_name}"
            
            return package_name
        
        # Not in a package - use parent directory name as context
        parent_name = parent.name
        if parent_name not in ('src', 'lib', 'scripts', '.'):
            return parent_name
        
        return None


def discover_workflows(
    search_paths: List[str],
    base_path: Optional[Path] = None,
    exclude_patterns: Optional[List[str]] = None,
    verbose: bool = False
) -> DiscoveryResult:
    """
    Convenience function to discover workflows.
    
    Args:
        search_paths: List of directories to scan.
        base_path: Base directory for relative paths.
        exclude_patterns: Patterns for files to exclude.
        verbose: Enable verbose logging.
    
    Returns:
        DiscoveryResult with discovered workflows.
    
    Example:
        result = discover_workflows(['protocols/', 'modules/'])
        
        for path, workflow in result.workflows.items():
            print(f"{workflow.display_name}: {workflow.declared_tiers}")
    """
    discovery = WorkflowDiscovery(
        base_path=base_path,
        exclude_patterns=exclude_patterns,
        verbose=verbose
    )
    return discovery.discover(search_paths)


# Sphinx integration helper
def build_workflow_registry(
    app,
    search_paths: Optional[List[str]] = None
) -> DiscoveryResult:
    """
    Build workflow registry for Sphinx integration.
    
    Reads search paths from Sphinx config if not provided.
    
    Args:
        app: Sphinx application object.
        search_paths: Override search paths (else use config).
    
    Returns:
        DiscoveryResult with discovered workflows.
    """
    # Get search paths from config if not provided
    if search_paths is None:
        search_paths = getattr(app.config, 'workflow_search_paths', [])
    
    if not search_paths:
        logger.warning("No workflow_search_paths configured")
        return DiscoveryResult()
    
    # Resolve base path from Sphinx source directory
    source_dir = Path(app.srcdir)
    base_path = source_dir.parent  # Go up from docs/ to project root
    
    # Get exclude patterns from config
    exclude_patterns = getattr(app.config, 'workflow_exclude_patterns', None)
    
    discovery = WorkflowDiscovery(
        base_path=base_path,
        exclude_patterns=exclude_patterns,
        verbose=getattr(app.config, 'workflow_verbose', False)
    )
    
    result = discovery.discover(search_paths)
    
    # Log results
    if result.workflows:
        logger.info(f"Discovered {len(result.workflows)} workflow modules")
    if result.errors:
        for error in result.errors:
            logger.warning(f"Discovery error: {error}")
    
    return result
