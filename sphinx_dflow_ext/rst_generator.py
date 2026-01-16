"""
RST (reStructuredText) generator for workflow documentation.

Converts workflow structure (steps, metadata, functions) into Sphinx-compatible
reStructuredText format with custom directives and formatting.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path


class WorkflowRSTGenerator:
    """Generate RST documentation from workflow structure."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize RST generator.
        
        Args:
            config: Workflow configuration from Sphinx
        """
        self.config = config
        self.show_diagrams = config.get('show_diagrams', True)
        self.collapse_substeps = config.get('collapse_substeps', True)
        self.show_function_calls = config.get('show_function_calls', True)
        self.max_substep_depth = config.get('max_substep_depth', 3)
        self._current_module_name = ''  # Module name for source linking
    
    def generate_module_rst(
        self,
        module_name: str,
        metadata: Dict[str, Any],
        steps: List[Any],
        all_functions: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Generate complete RST documentation for a module workflow.
        
        Args:
            module_name: Module name
            metadata: Workflow metadata
            steps: List of workflow steps
            all_functions: Hierarchical function documentation (optional)
        
        Returns:
            List of RST lines
        """
        # Store module name for source linking
        self._current_module_name = module_name
        
        lines = []
        
        # Add workflow header
        lines.extend(self._generate_header(module_name, metadata))
        lines.append("")
        
        # Add metadata section
        if metadata:
            lines.extend(self._generate_metadata_section(metadata))
            lines.append("")
        
        # Add quick reference table
        if steps:
            lines.extend(self._generate_quick_reference(steps))
            lines.append("")
        
        # Add workflow diagram
        if self.show_diagrams and steps:
            lines.extend(self._generate_diagram(steps))
            lines.append("")
        
        # Add detailed workflow steps
        if steps:
            lines.extend(self._generate_steps_section(steps, module_name))
            lines.append("")
        
        # Note: Function Call Hierarchy section removed - this information
        # is now included within the hierarchical Detailed Workflow section
        
        return lines
    
    def _generate_header(self, module_name: str, metadata: Dict[str, Any]) -> List[str]:
        """Generate workflow header section."""
        lines = []
        
        # Main title - use rubric to avoid section nesting issues
        title = f"{module_name} - Workflow Protocol"
        lines.append(f".. rubric:: {title}")
        lines.append("   :class: workflow-main-title")
        lines.append("")
        
        # Analysis type if available
        if metadata.get('analysis_type'):
            lines.append(f"**Analysis Type:** {metadata['analysis_type']}")
            lines.append("")
        
        return lines
    
    def _generate_metadata_section(self, metadata: Dict[str, Any]) -> List[str]:
        """Generate metadata section."""
        lines = []
        
        lines.append(".. rubric:: Workflow Metadata")
        lines.append("")
        
        # Build field list
        if metadata.get('description'):
            lines.append(f":Description: {metadata['description']}")
        
        if metadata.get('tier'):
            lines.append(f":Tier: {metadata['tier']}")
        
        if metadata.get('entry_point'):
            lines.append(f":Entry Point: ``{metadata['entry_point']}()``")
        
        if metadata.get('protocol_version'):
            lines.append(f":Protocol Version: {metadata['protocol_version']}")
        
        lines.append("")
        
        return lines
    
    def _generate_quick_reference(self, steps: List[Any]) -> List[str]:
        """Generate quick reference table."""
        lines = []
        
        lines.append(".. rubric:: Quick Reference")
        lines.append("")
        
        # Create table
        lines.append(".. list-table::")
        lines.append("   :header-rows: 1")
        lines.append("   :widths: 10 40 30 20")
        lines.append("")
        lines.append("   * - Step")
        lines.append("     - Description")
        lines.append("     - Key Functions")
        lines.append("     - Notes")
        
        for step in steps:
            step_num = step.number
            step_name = step.name
            
            # Get functions
            functions = []
            if hasattr(step, 'function_name') and step.function_name:
                functions.append(f"``{step.function_name}()``")
            
            # Get sub-step functions
            if hasattr(step, 'sub_steps'):
                for substep in step.sub_steps:
                    if hasattr(substep, 'function_name') and substep.function_name:
                        if f"``{substep.function_name}()``" not in functions:
                            functions.append(f"``{substep.function_name}()``")
            
            functions_str = ", ".join(functions) if functions else "—"
            
            # Check for critical markers
            notes = []
            if hasattr(step, 'critical') and step.critical:
                notes.append("⚠️ " + step.critical)
            
            notes_str = " ".join(notes) if notes else "—"
            
            lines.append(f"   * - {step_num}")
            lines.append(f"     - {step_name}")
            lines.append(f"     - {functions_str}")
            lines.append(f"     - {notes_str}")
        
        lines.append("")
        
        return lines
    
    def _generate_diagram(self, steps: List[Any]) -> List[str]:
        """Generate Mermaid flowchart diagram."""
        lines = []
        
        lines.append(".. rubric:: Workflow Diagram")
        lines.append("")
        lines.append(".. mermaid::")
        lines.append("")
        lines.append("   graph TD")
        lines.append("       Start([Start]) --> Step1")
        
        for i, step in enumerate(steps, 1):
            step_id = f"Step{i}"
            step_label = f"{step.number}: {step.name}"
            
            # Escape special characters
            step_label = step_label.replace('"', '\\"')
            
            # Add step node
            lines.append(f"       {step_id}[\"{step_label}\"]")
            
            # Link to next step
            if i < len(steps):
                next_step_id = f"Step{i+1}"
                lines.append(f"       {step_id} --> {next_step_id}")
            else:
                lines.append(f"       {step_id} --> End([End])")
        
        lines.append("")
        
        return lines
    
    def _generate_steps_section(self, steps: List[Any], module_name: str = '') -> List[str]:
        """Generate detailed workflow steps section."""
        lines = []
        
        lines.append(".. rubric:: Detailed Workflow")
        lines.append("")
        
        # Generate navigation box for major steps only
        lines.append(".. admonition:: Quick Navigation")
        lines.append("   :class: workflow-step-nav")
        lines.append("")
        for i, step in enumerate(steps, 1):
            step_num = step.number
            step_name = step.name
            lines.append(f"   - :ref:`Step {step_num}: {step_name} <step-{step_num}>`")
        lines.append("")
        
        for step in steps:
            lines.extend(self._generate_step_detail(step, module_name=module_name))
            lines.append("")
        
        return lines
    
    def _generate_step_detail(self, step: Any, depth: int = 0, module_name: str = '') -> List[str]:
        """Generate detailed documentation for a single step."""
        lines = []
        indent = "   " * depth
        
        # Get the step number (hierarchical if available, otherwise regular)
        step_number = getattr(step, 'hierarchical_number', getattr(step, 'number', ''))
        
        # Step header with hierarchical numbering
        step_title = f"Step {step_number}: {step.name}"
        
        # Add anchor for major steps (depth 0) to enable navigation
        if depth == 0:
            lines.append(f".. _step-{step_number}:")
            lines.append("")
        
        # Use custom directive/class for proper styling
        lines.append(f"{indent}.. container:: workflow-step workflow-step-depth-{depth}")
        lines.append(f"{indent}")
        
        # Build step title with optional source link
        source_module = getattr(step, 'source_module', module_name) or module_name
        source_line = getattr(step, 'source_line', None)
        
        if source_module and source_line:
            # Add source link after title
            step_anchor = f"step-{str(step_number).replace('.', '-')}"
            source_link = f":source-link:`{source_module}#{step_anchor}`"
            lines.append(f"{indent}   .. rubric:: {step_title} {source_link}")
        else:
            lines.append(f"{indent}   .. rubric:: {step_title}")
        
        lines.append(f"{indent}      :class: workflow-step-title")
        lines.append(f"{indent}")
        
        # Purpose
        if hasattr(step, 'purpose') and step.purpose:
            lines.append(f"{indent}   **Purpose:** {step.purpose}")
            lines.append(f"{indent}")
        
        # Function signature
        if hasattr(step, 'function_name') and step.function_name:
            func_name = step.function_name
            
            # Try to get signature
            if hasattr(step, 'function_signature') and step.function_signature:
                sig = step.function_signature
                lines.append(f"{indent}   .. code-block:: python")
                lines.append(f"{indent}")
                lines.append(f"{indent}      {sig}")
                lines.append(f"{indent}")
            else:
                lines.append(f"{indent}   **Function:** ``{func_name}()``")
                lines.append(f"{indent}")
        
        # Inputs/Outputs in field list
        if hasattr(step, 'inputs') and step.inputs:
            inputs_str = ", ".join(step.inputs)
            lines.append(f"{indent}   :Inputs: {inputs_str}")
        
        if hasattr(step, 'outputs') and step.outputs:
            outputs_str = ", ".join(step.outputs)
            lines.append(f"{indent}   :Outputs: {outputs_str}")
        
        if (hasattr(step, 'inputs') and step.inputs) or (hasattr(step, 'outputs') and step.outputs):
            lines.append(f"{indent}")
        
        # Critical warnings
        if hasattr(step, 'critical') and step.critical:
            lines.append(f"{indent}   .. warning::")
            lines.append(f"{indent}")
            lines.append(f"{indent}      {step.critical}")
            lines.append(f"{indent}")
        
        # Sub-steps
        if hasattr(step, 'sub_steps') and step.sub_steps:
            if self.collapse_substeps:
                # Collapsible section using sphinx-design dropdown
                lines.append(f"{indent}   .. dropdown:: Sub-steps ({len(step.sub_steps)})")
                lines.append(f"{indent}      :animate: fade-in")
                lines.append(f"{indent}")
                
                for substep in step.sub_steps:
                    substep_lines = self._generate_step_detail(substep, depth + 1, module_name=source_module)
                    for line in substep_lines:
                        lines.append(f"{indent}      {line}")
            else:
                # Always expanded - nest substeps inside container
                for substep in step.sub_steps:
                    substep_lines = self._generate_step_detail(substep, depth + 1, module_name=source_module)
                    for line in substep_lines:
                        lines.append(f"{indent}   {line}")
        
        return lines
    
    def _generate_function_hierarchy(self, all_functions: Dict[str, Any]) -> List[str]:
        """Generate hierarchical function documentation."""
        lines = []
        
        lines.append("")
        lines.append(".. rubric:: Function Call Hierarchy")
        lines.append("")
        lines.append("This section shows the internal workflow steps within each function.")
        lines.append("")
        
        for func_name, func_data in all_functions.items():
            # Use rubric instead of section title to avoid nesting issues
            lines.append(f".. rubric:: ``{func_name}()``")
            lines.append("")
            
            # Handle various formats robustly
            try:
                # Check for list format first (most common now)
                if isinstance(func_data, (list, tuple)):
                    # New format: list of StepInfo objects
                    for step in func_data:
                        lines.extend(self._generate_step_detail(step, depth=1))
                        lines.append("")
                elif isinstance(func_data, dict):
                    # Legacy format: dict with 'docstring' and 'steps'
                    docstring = func_data.get('docstring')
                    if docstring:
                        lines.append(str(docstring))
                        lines.append("")
                    
                    steps = func_data.get('steps')
                    if steps:
                        for step in steps:
                            lines.extend(self._generate_step_detail(step, depth=1))
                            lines.append("")
                elif hasattr(func_data, '__iter__'):
                    # Fallback: try iterating over it
                    for step in func_data:
                        lines.extend(self._generate_step_detail(step, depth=1))
                        lines.append("")
            except Exception as e:
                # Log error but continue with other functions
                lines.append(f"   *Error processing function steps: {e}*")
                lines.append("")
        
        return lines
    
    def generate_notebook_rst(
        self,
        notebook_name: str,
        metadata: Dict[str, Any],
        steps: List[Any],
        outputs: List[Any],
        issues: List[Any]
    ) -> List[str]:
        """
        Generate RST documentation for notebook workflows.
        
        Args:
            notebook_name: Notebook filename
            metadata: Workflow metadata
            steps: List of workflow steps
            outputs: Output artifacts
            issues: Common issues
        
        Returns:
            List of RST lines
        """
        lines = []
        
        # Header
        title = f"{notebook_name} - Workflow"
        lines.append(title)
        lines.append("=" * len(title))
        lines.append("")
        
        # Metadata
        if metadata:
            lines.extend(self._generate_metadata_section(metadata))
            lines.append("")
        
        # Quick reference
        if steps:
            lines.extend(self._generate_quick_reference(steps))
            lines.append("")
        
        # Detailed steps
        if steps:
            lines.extend(self._generate_steps_section(steps))
            lines.append("")
        
        # Output artifacts
        if outputs:
            lines.extend(self._generate_outputs_section(outputs))
            lines.append("")
        
        # Common issues
        if issues:
            lines.extend(self._generate_issues_section(issues))
            lines.append("")
        
        return lines
    
    def _generate_outputs_section(self, outputs: List[Any]) -> List[str]:
        """Generate output artifacts section."""
        lines = []
        
        lines.append("Output Artifacts")
        lines.append("-" * 16)
        lines.append("")
        
        for output in outputs:
            lines.append(f"- **{output.name}**")
            if output.description:
                lines.append(f"  {output.description}")
            lines.append("")
        
        return lines
    
    def _generate_issues_section(self, issues: List[Any]) -> List[str]:
        """Generate common issues section."""
        lines = []
        
        lines.append("Common Issues")
        lines.append("-" * 13)
        lines.append("")
        
        for issue in issues:
            lines.append(f"**{issue.title}**")
            lines.append("")
            lines.append(issue.description)
            lines.append("")
            
            if issue.solution:
                lines.append("*Solution:*")
                lines.append("")
                lines.append(issue.solution)
                lines.append("")
        
        return lines
