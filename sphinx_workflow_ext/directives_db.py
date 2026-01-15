"""
Database-backed Sphinx directives for workflow documentation.

These directives read workflow data from the generate_workflow_docs database
instead of extracting directly from source files.

Provides:
- .. workflow-db:: - Render workflow from database
- .. workflow-index-db:: - Auto-generated index from database
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from docutils import nodes
from docutils.parsers.rst import Directive, directives
from docutils.statemachine import StringList
from sphinx.util import logging as sphinx_logging

from .db_adapter import DatabaseAdapter, WorkflowData, StepData
from .rst_generator import WorkflowRSTGenerator

logger = sphinx_logging.getLogger(__name__)


class WorkflowDBDirective(Directive):
    """
    Directive to render workflow from database.
    
    This is the database-backed version that reads pre-extracted data
    instead of parsing source files directly.
    
    Usage:
        .. workflow-db:: src/cli.py
           :tier: detailed
           :show-diagram: true
        
        .. workflow-db:: src.cli:cmd_scan
           :tier: overview
    
    Target formats:
        - "src/cli.py" - Module path (shows all functions with steps)
        - "src.cli:cmd_scan" - Specific function
        - "cmd_scan" - Function name (searches all modules)
    
    Options:
        tier: Display tier (overview, detailed, full) - default: detailed
        show-diagram: Show Mermaid flowchart - default: true
        collapse-substeps: Collapse sub-steps by default - default: true
        no-collapse-substeps: Show sub-steps expanded (no dropdown)
        show-source-links: Link steps to source code - default: true
    """
    
    required_arguments = 1  # Target (module path or function)
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {
        'tier': directives.unchanged,
        'show-diagram': directives.flag,
        'no-diagram': directives.flag,
        'collapse-substeps': directives.flag,
        'no-collapse-substeps': directives.flag,
        'show-source-links': directives.flag,
    }
    has_content = False
    
    def run(self) -> List[nodes.Node]:
        """Execute the directive."""
        target = self.arguments[0]
        
        # Get Sphinx environment
        env = self.state.document.settings.env
        source_dir = Path(env.srcdir).parent  # Go up from docs/ to project root
        
        # Check for custom database path in config
        db_path = None
        if hasattr(env.config, 'workflow_db_path') and env.config.workflow_db_path:
            db_path = Path(env.srcdir) / env.config.workflow_db_path
            if db_path.exists():
                source_dir = db_path.parent.parent  # Project root is 2 levels up from .workflow/workflow.db
        
        # Get options
        tier = self.options.get('tier', 'detailed')
        show_diagram = 'no-diagram' not in self.options  # Default True
        collapse_substeps = 'no-collapse-substeps' not in self.options  # Default True (use dropdown)
        show_source_links = 'show-source-links' not in self.options  # Default True
        
        try:
            # Initialize database adapter
            adapter = DatabaseAdapter(source_dir, db_path=db_path)
            
            # Determine if target is a module or function
            if ":" in target:
                # Function target: module:function
                workflow = adapter.get_function_workflow(target)
            elif target.endswith(".py"):
                # Module path
                workflow = adapter.get_module_workflow(target)
            else:
                # Try as function name first, then module name
                workflow = adapter.get_function_workflow(target)
                if not workflow:
                    workflow = adapter.get_module_workflow(target)
            
            if not workflow:
                logger.error(f"Workflow not found in database: {target}")
                error = self.state_machine.reporter.error(
                    f'Workflow not found in database: {target}. '
                    f'Run "workflow-steps scan" first.',
                    nodes.literal_block('', ''),
                    line=self.lineno
                )
                return [error]
            
            # Store source mappings for source page generation
            if show_source_links:
                self._store_source_mappings(env, workflow, source_dir)
            
            # Generate RST content
            rst_lines = self._generate_rst(
                workflow, tier, show_diagram, collapse_substeps, show_source_links
            )
            
            # Parse RST into nodes
            node = nodes.container()
            node['classes'].append('workflow-container')
            rst_lines_list = StringList(rst_lines, source='workflow-db-directive')
            self.state.nested_parse(
                rst_lines_list,
                self.content_offset,
                node
            )
            
            return [node]
            
        except FileNotFoundError as e:
            logger.error(str(e))
            error = self.state_machine.reporter.error(
                str(e),
                nodes.literal_block('', ''),
                line=self.lineno
            )
            return [error]
        except Exception as e:
            logger.error(f"Error loading workflow: {e}")
            import traceback
            traceback.print_exc()
            error = self.state_machine.reporter.error(
                f'Error loading workflow from database: {e}',
                nodes.literal_block('', ''),
                line=self.lineno
            )
            return [error]
    
    def _store_source_mappings(self, env, workflow: WorkflowData, source_dir: Path):
        """
        Store source mappings in Sphinx environment for source page generation.
        
        This enables the source_generator.py to create the 2-column workflow
        browser pages at build-finished time.
        """
        if not hasattr(env, 'workflow_source_mappings'):
            env.workflow_source_mappings = {}
        
        # Build module name from workflow
        module_name = workflow.module_name
        source_path = str(source_dir / workflow.module_path) if workflow.module_path else ''
        
        # Build step data mapping
        step_data = {}
        for func in workflow.functions:
            for step in func.steps:
                self._collect_step_data(step, func.name, module_name, step_data)
        
        # Store or merge with existing
        if module_name in env.workflow_source_mappings:
            existing = env.workflow_source_mappings[module_name]
            existing['steps'].update(step_data)
        else:
            env.workflow_source_mappings[module_name] = {
                'source_path': source_path,
                'steps': step_data
            }
    
    def _collect_step_data(
        self, 
        step: StepData, 
        func_name: str,
        module_name: str, 
        step_data: dict
    ):
        """Recursively collect step data for source mapping."""
        step_id = f"step-{step.number.replace('.', '-')}"
        step_data[step_id] = {
            'line': step.line,
            'name': step.name,
            'number': step.number,
            'module': module_name,
            'function': func_name
        }
        
        for sub in step.sub_steps:
            self._collect_step_data(sub, func_name, module_name, step_data)
    
    def _generate_rst(
        self,
        workflow: WorkflowData,
        tier: str,
        show_diagram: bool,
        collapse_substeps: bool,
        show_source_links: bool = True
    ) -> List[str]:
        """
        Generate RST content for a workflow.
        
        Args:
            workflow: WorkflowData from database
            tier: Display tier (overview, detailed, full)
            show_diagram: Whether to show Mermaid diagram
            collapse_substeps: Whether to collapse sub-steps
            show_source_links: Whether to add [source] links
        
        Returns:
            List of RST lines
        """
        lines = []
        module_name = workflow.module_name
        
        # For each function with steps
        for func in workflow.functions:
            if not func.steps:
                continue
            
            # Function header
            lines.append(f"**{func.name}**")
            lines.append("")
            
            if tier in ('detailed', 'full') and func.docstring:
                # Add first line of docstring
                first_line = func.docstring.split('\n')[0].strip()
                if first_line:
                    lines.append(f"*{first_line}*")
                    lines.append("")
            
            # Mermaid diagram
            if show_diagram:
                lines.extend(self._generate_diagram(func.steps))
                lines.append("")
            
            # Steps
            lines.extend(self._generate_steps_rst(
                func.steps, tier, collapse_substeps, 
                show_source_links=show_source_links,
                module_name=module_name
            ))
            lines.append("")
        
        return lines
    
    def _generate_diagram(self, steps: List[StepData]) -> List[str]:
        """Generate Mermaid flowchart for steps."""
        lines = [
            ".. mermaid::",
            "",
            "   flowchart TD",
        ]
        
        prev_id = None
        for step in steps:
            step_id = f"S{step.number.replace('.', '_')}"
            label = f"{step.number}: {step.name}"
            # Escape special chars for Mermaid
            label = label.replace('"', "'")
            lines.append(f'      {step_id}["{label}"]')
            
            if prev_id:
                lines.append(f"      {prev_id} --> {step_id}")
            prev_id = step_id
            
            # Add sub-steps
            for sub in step.sub_steps:
                sub_id = f"S{sub.number.replace('.', '_')}"
                sub_label = f"{sub.number}: {sub.name}"
                sub_label = sub_label.replace('"', "'")
                lines.append(f'      {sub_id}["{sub_label}"]')
                lines.append(f"      {step_id} --> {sub_id}")
        
        lines.append("")
        return lines
    
    def _generate_steps_rst(
        self,
        steps: List[StepData],
        tier: str,
        collapse_substeps: bool,
        indent: int = 0,
        show_source_links: bool = True,
        module_name: str = ""
    ) -> List[str]:
        """Generate RST for a list of steps with proper styling."""
        lines = []
        base_indent = "   " * indent
        
        for step in steps:
            step_number = step.number
            step_title = f"Step {step_number}: {step.name}"
            
            # Add anchor for top-level steps
            if indent == 0:
                lines.append(f".. _step-{step_number}:")
                lines.append("")
            
            # Use container for box styling
            lines.append(f"{base_indent}.. container:: workflow-step workflow-step-depth-{indent}")
            lines.append(f"{base_indent}")
            
            # Build step title with optional source link
            if show_source_links and module_name and step.line:
                step_anchor = f"step-{step_number.replace('.', '-')}"
                source_link = f":source-link:`{module_name}#{step_anchor}`"
                lines.append(f"{base_indent}   .. rubric:: {step_title} {source_link}")
            else:
                lines.append(f"{base_indent}   .. rubric:: {step_title}")
            lines.append(f"{base_indent}      :class: workflow-step-title")
            lines.append(f"{base_indent}")
            
            # Purpose
            if tier in ('detailed', 'full') and step.purpose:
                lines.append(f"{base_indent}   **Purpose:** {step.purpose}")
                lines.append(f"{base_indent}")
            
            # Inputs/Outputs as field list (full tier only)
            if tier == 'full':
                if step.inputs:
                    lines.append(f"{base_indent}   :Inputs: {step.inputs}")
                if step.outputs:
                    lines.append(f"{base_indent}   :Outputs: {step.outputs}")
                if step.inputs or step.outputs:
                    lines.append(f"{base_indent}")
            
            # Critical warnings
            if step.critical:
                lines.append(f"{base_indent}   .. warning::")
                lines.append(f"{base_indent}")
                lines.append(f"{base_indent}      {step.critical}")
                lines.append(f"{base_indent}")
            
            # Sub-steps with dropdown
            if step.sub_steps:
                if collapse_substeps:
                    # Collapsible section using sphinx-design dropdown
                    lines.append(f"{base_indent}   .. dropdown:: Sub-steps ({len(step.sub_steps)})")
                    lines.append(f"{base_indent}      :animate: fade-in")
                    lines.append(f"{base_indent}")
                    
                    substep_lines = self._generate_steps_rst(
                        step.sub_steps, tier, collapse_substeps, indent + 1,
                        show_source_links=show_source_links, module_name=module_name
                    )
                    for line in substep_lines:
                        lines.append(f"{base_indent}      {line}")
                else:
                    # Always expanded
                    substep_lines = self._generate_steps_rst(
                        step.sub_steps, tier, collapse_substeps, indent + 1,
                        show_source_links=show_source_links, module_name=module_name
                    )
                    for line in substep_lines:
                        lines.append(f"{base_indent}   {line}")
            
            lines.append("")
        
        return lines


class WorkflowIndexDBDirective(Directive):
    """
    Directive to generate an index of all workflows from database.
    
    Usage:
        .. workflow-index-db::
           :group-by: module
           :show-step-counts: true
    
    Options:
        group-by: How to group workflows (module, package, none) - default: module
        show-step-counts: Show number of steps per function - default: true
    """
    
    required_arguments = 0
    optional_arguments = 0
    option_spec = {
        'group-by': directives.unchanged,
        'show-step-counts': directives.flag,
        'hide-step-counts': directives.flag,
    }
    has_content = False
    
    def run(self) -> List[nodes.Node]:
        """Execute the directive."""
        # Get Sphinx environment
        env = self.state.document.settings.env
        source_dir = Path(env.srcdir).parent
        
        # Get options
        group_by = self.options.get('group-by', 'module')
        show_step_counts = 'hide-step-counts' not in self.options
        
        try:
            adapter = DatabaseAdapter(source_dir)
            workflows = adapter.get_all_workflows()
            
            if not workflows:
                lines = [
                    ".. note::",
                    "",
                    "   No workflows found in database.",
                    "   Run ``workflow-steps scan`` to populate the database.",
                    ""
                ]
            else:
                lines = self._generate_index(workflows, group_by, show_step_counts)
            
            # Parse RST into nodes
            node = nodes.container()
            node['classes'].append('workflow-index')
            rst_lines_list = StringList(lines, source='workflow-index-db-directive')
            self.state.nested_parse(
                rst_lines_list,
                self.content_offset,
                node
            )
            
            return [node]
            
        except FileNotFoundError as e:
            logger.error(str(e))
            error = self.state_machine.reporter.error(
                str(e),
                nodes.literal_block('', ''),
                line=self.lineno
            )
            return [error]
        except Exception as e:
            logger.error(f"Error generating workflow index: {e}")
            error = self.state_machine.reporter.error(
                f'Error generating workflow index: {e}',
                nodes.literal_block('', ''),
                line=self.lineno
            )
            return [error]
    
    def _generate_index(
        self,
        workflows: List[WorkflowData],
        group_by: str,
        show_step_counts: bool
    ) -> List[str]:
        """Generate RST index content."""
        lines = []
        
        if group_by == 'module':
            for workflow in sorted(workflows, key=lambda w: w.module_name):
                lines.append(f"**{workflow.module_name}** ({workflow.module_path})")
                lines.append("")
                
                for func in workflow.functions:
                    if func.steps:
                        step_count = self._count_all_steps(func.steps)
                        if show_step_counts:
                            lines.append(f"- ``{func.name}`` - {step_count} steps")
                        else:
                            lines.append(f"- ``{func.name}``")
                
                lines.append("")
        else:
            # Flat list
            for workflow in sorted(workflows, key=lambda w: w.name):
                for func in workflow.functions:
                    if func.steps:
                        step_count = self._count_all_steps(func.steps)
                        if show_step_counts:
                            lines.append(f"- ``{workflow.module_name}.{func.name}`` - {step_count} steps")
                        else:
                            lines.append(f"- ``{workflow.module_name}.{func.name}``")
            lines.append("")
        
        return lines
    
    def _count_all_steps(self, steps: List[StepData]) -> int:
        """Count total steps including sub-steps."""
        count = len(steps)
        for step in steps:
            count += self._count_all_steps(step.sub_steps)
        return count


def setup_db_directives(app):
    """Register database-backed directives with Sphinx."""
    app.add_directive('workflow-db', WorkflowDBDirective)
    app.add_directive('workflow-index-db', WorkflowIndexDBDirective)
