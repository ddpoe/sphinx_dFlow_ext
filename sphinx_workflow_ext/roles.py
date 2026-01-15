"""
Custom Sphinx roles for inline workflow references.

Provides:
- :workflow-step:`module:Step X` - Reference a specific workflow step
"""

from docutils import nodes
from sphinx.util import logging as sphinx_logging

logger = sphinx_logging.getLogger(__name__)


def workflow_step_role(name, rawtext, text, lineno, inliner, options=None, content=None):
    """
    Role to reference a specific workflow step.
    
    Usage:
        :workflow-step:`model_selection:Step 3.2`
    
    Args:
        name: Role name
        rawtext: Full role text including markup
        text: Role content (e.g., "model_selection:Step 3.2")
        lineno: Line number
        inliner: Inliner object
        options: Options dict
        content: Content list
    
    Returns:
        Tuple of (nodes, messages)
    """
    if options is None:
        options = {}
    if content is None:
        content = []
    
    # Parse step reference
    if ':' in text:
        module_name, step_ref = text.split(':', 1)
    else:
        module_name = ''
        step_ref = text
    
    # Create reference node
    ref_text = step_ref
    if module_name:
        ref_text = f"{module_name} → {step_ref}"
    
    # Create a strong emphasis node for the step reference
    node = nodes.strong(rawtext, ref_text)
    node['classes'].append('workflow-step-ref')
    
    # Add title attribute for hover text
    if module_name:
        node['title'] = f"Workflow step {step_ref} in {module_name}"
    else:
        node['title'] = f"Workflow step {step_ref}"
    
    return [node], []
