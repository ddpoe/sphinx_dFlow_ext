"""
Database adapter for reading workflow data from document_workflow database.

This module provides the bridge between the Sphinx extension and the 
workflow database created by dFlow (document_workflow). Instead of extracting
workflows directly from source files, this reads pre-extracted data from
the SQLite database.

Architecture:
    Source Code → document_workflow (scan) → Database
    Database → sphinx_dflow_ext (db_adapter) → RST/HTML
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class StepData:
    """Step data in a format compatible with existing RST generator."""
    
    number: str  # "1", "2.1", etc.
    name: str
    purpose: Optional[str] = None
    inputs: Optional[str] = None
    outputs: Optional[str] = None
    critical: Optional[str] = None
    line: int = 0
    sub_steps: List["StepData"] = field(default_factory=list)
    
    # For compatibility with existing code
    hierarchical_number: str = ""
    source_line: int = 0
    
    def __post_init__(self):
        self.hierarchical_number = self.number
        self.source_line = self.line


@dataclass
class FunctionData:
    """Function data in a format compatible with existing RST generator."""
    
    name: str
    signature: Optional[str] = None
    docstring: Optional[str] = None
    line_start: int = 0
    line_end: int = 0
    steps: List[StepData] = field(default_factory=list)
    module_path: str = ""


@dataclass
class ModuleData:
    """Module data with all its functions and steps."""
    
    path: str
    module_name: str
    functions: List[FunctionData] = field(default_factory=list)


@dataclass
class WorkflowData:
    """Complete workflow data for rendering."""
    
    name: str
    module_name: str
    module_path: str
    functions: List[FunctionData] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class DatabaseAdapter:
    """
    Adapter to read workflow data from the generate_workflow_docs database.
    
    This replaces direct source extraction with database queries.
    
    Example:
        adapter = DatabaseAdapter(project_root)
        
        # Get workflow for a module
        workflow = adapter.get_module_workflow("src/cli.py")
        
        # Get workflow for a specific function
        workflow = adapter.get_function_workflow("src.cli:cmd_scan")
        
        # List all available modules
        modules = adapter.list_modules()
    """
    
    def __init__(self, project_root: Path, db_path: Optional[Path] = None):
        """
        Initialize the database adapter.
        
        Args:
            project_root: Project root directory
            db_path: Optional explicit database path (default: .workflow/workflow.db)
        """
        self.project_root = Path(project_root).resolve()
        self.db_path = db_path or (self.project_root / ".workflow" / "workflow.db")
        
        self._engine = None
        self._session_factory = None
    
    def _ensure_connection(self):
        """Lazily initialize database connection."""
        if self._engine is not None:
            return
        
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Workflow database not found at {self.db_path}. "
                f"Run 'workflow-steps scan' first to populate the database."
            )
        
        from sqlmodel import create_engine
        
        self._engine = create_engine(f"sqlite:///{self.db_path}", echo=False)
    
    def _get_session(self):
        """Get a database session."""
        from sqlmodel import Session
        self._ensure_connection()
        return Session(self._engine)
    
    def list_modules(self) -> List[ModuleData]:
        """
        List all modules in the database.
        
        Returns:
            List of ModuleData with basic info (no steps loaded)
        """
        # Import here to avoid circular deps
        from sqlmodel import select
        
        # Import tables from document_workflow
        try:
            from document_workflow.db.tables import Module
        except ImportError:
            # Try alternative import path
            import sys
            sys.path.insert(0, str(self.project_root.parent))
            from document_workflow.db.tables import Module
        
        session = self._get_session()
        try:
            modules = session.exec(select(Module)).all()
            return [
                ModuleData(
                    path=m.path,
                    module_name=m.module_name,
                    functions=[]  # Don't load functions for listing
                )
                for m in modules
            ]
        finally:
            session.close()
    
    def get_module_workflow(self, module_path: str) -> Optional[WorkflowData]:
        """
        Get complete workflow data for a module.
        
        Args:
            module_path: Path to module (relative or absolute)
        
        Returns:
            WorkflowData with all functions and steps, or None if not found
        """
        from sqlmodel import select
        
        try:
            from document_workflow.db.tables import Module, Function, Step
        except ImportError:
            import sys
            sys.path.insert(0, str(self.project_root.parent))
            from document_workflow.db.tables import Module, Function, Step
        
        # Normalize path
        path = Path(module_path)
        if path.is_absolute():
            try:
                rel_path = str(path.relative_to(self.project_root))
            except ValueError:
                rel_path = str(path)
        else:
            rel_path = str(path)
        
        session = self._get_session()
        try:
            # Find module
            module = session.exec(
                select(Module).where(Module.path == rel_path)
            ).first()
            
            if not module:
                # Try matching by module name
                module = session.exec(
                    select(Module).where(Module.module_name == Path(rel_path).stem)
                ).first()
            
            if not module:
                logger.warning(f"Module not found in database: {rel_path}")
                return None
            
            # Load functions with steps
            functions = []
            for func in module.functions:
                steps = self._build_step_hierarchy(func.steps)
                functions.append(FunctionData(
                    name=func.name,
                    signature=func.signature,
                    docstring=func.docstring,
                    line_start=func.line_start,
                    line_end=func.line_end or func.line_start,
                    steps=steps,
                    module_path=module.path
                ))
            
            return WorkflowData(
                name=module.module_name,
                module_name=module.module_name,
                module_path=module.path,
                functions=functions,
                metadata={
                    "path": module.path,
                    "last_scanned": str(module.last_scanned) if module.last_scanned else None
                }
            )
        finally:
            session.close()
    
    def get_function_workflow(self, target: str) -> Optional[WorkflowData]:
        """
        Get workflow data for a specific function.
        
        Args:
            target: Function target in format "module.path:function_name" or just "function_name"
        
        Returns:
            WorkflowData with just the requested function, or None if not found
        """
        from sqlmodel import select
        
        try:
            from document_workflow.db.tables import Module, Function, Step
        except ImportError:
            import sys
            sys.path.insert(0, str(self.project_root.parent))
            from document_workflow.db.tables import Module, Function, Step
        
        # Parse target
        if ":" in target:
            module_part, func_name = target.rsplit(":", 1)
        else:
            module_part = None
            func_name = target
        
        session = self._get_session()
        try:
            # Build query
            query = select(Function).where(Function.name == func_name)
            
            if module_part:
                # Normalize path separators for cross-platform matching
                # Database may have backslashes on Windows
                # Only convert path separators, not dots in filenames
                module_search_fwd = module_part.replace("\\", "/")  # Forward slash version
                module_search_back = module_part.replace("/", "\\")  # Backslash version
                
                # Join with module to filter by path (try both separators)
                query = (
                    select(Function)
                    .join(Module)
                    .where(Function.name == func_name)
                    .where(
                        Module.path.contains(module_search_fwd) | 
                        Module.path.contains(module_search_back)
                    )
                )
            
            func = session.exec(query).first()
            
            if not func:
                logger.warning(f"Function not found in database: {target}")
                return None
            
            # Load the module for context
            module = func.module
            
            # Build step hierarchy
            steps = self._build_step_hierarchy(func.steps)
            
            function_data = FunctionData(
                name=func.name,
                signature=func.signature,
                docstring=func.docstring,
                line_start=func.line_start,
                line_end=func.line_end or func.line_start,
                steps=steps,
                module_path=module.path if module else ""
            )
            
            return WorkflowData(
                name=f"{module.module_name}.{func.name}" if module else func.name,
                module_name=module.module_name if module else "",
                module_path=module.path if module else "",
                functions=[function_data],
                metadata={
                    "function": func.name,
                    "path": module.path if module else None
                }
            )
        finally:
            session.close()
    
    def _build_step_hierarchy(self, steps: List[Any]) -> List[StepData]:
        """
        Build hierarchical step structure from flat database steps.
        
        Converts flat list of steps with numbers like "1", "2", "2.1", "2.2"
        into nested StepData objects.
        
        Args:
            steps: List of Step database objects
        
        Returns:
            List of StepData with sub_steps populated
        """
        if not steps:
            return []
        
        # Sort by step number
        sorted_steps = sorted(steps, key=lambda s: self._step_sort_key(s.step_number))
        
        # Build hierarchy
        root_steps: List[StepData] = []
        step_map: Dict[str, StepData] = {}
        
        for step in sorted_steps:
            step_data = StepData(
                number=step.step_number,
                name=step.name,
                purpose=step.purpose,
                inputs=step.inputs,
                outputs=step.outputs,
                critical=step.critical,
                line=step.line,
                sub_steps=[]
            )
            
            step_map[step.step_number] = step_data
            
            # Determine parent
            if "." in step.step_number:
                # This is a sub-step, find parent
                parent_num = step.step_number.rsplit(".", 1)[0]
                if parent_num in step_map:
                    step_map[parent_num].sub_steps.append(step_data)
                else:
                    # Parent not found, add as root
                    root_steps.append(step_data)
            else:
                # Root step
                root_steps.append(step_data)
        
        return root_steps
    
    def _step_sort_key(self, step_number: str) -> tuple:
        """
        Generate sort key for step numbers.
        
        "1" -> (1,)
        "2" -> (2,)
        "2.1" -> (2, 1)
        "2.10" -> (2, 10)
        """
        parts = step_number.split(".")
        return tuple(int(p) for p in parts if p.isdigit())
    
    def get_all_workflows(self) -> List[WorkflowData]:
        """
        Get all workflows from all modules.
        
        Returns:
            List of WorkflowData for all modules with steps
        """
        modules = self.list_modules()
        workflows = []
        
        for mod in modules:
            workflow = self.get_module_workflow(mod.path)
            if workflow and any(f.steps for f in workflow.functions):
                workflows.append(workflow)
        
        return workflows
    
    def get_modules_with_steps(self) -> List[str]:
        """
        Get list of module paths that have at least one step.
        
        Returns:
            List of module paths
        """
        from sqlmodel import select, func
        
        try:
            from document_workflow.db.tables import Module, Function, Step
        except ImportError:
            import sys
            sys.path.insert(0, str(self.project_root.parent))
            from document_workflow.db.tables import Module, Function, Step
        
        session = self._get_session()
        try:
            # Query modules that have functions with steps
            result = session.exec(
                select(Module.path)
                .join(Function)
                .join(Step)
                .distinct()
            ).all()
            
            return list(result)
        finally:
            session.close()
