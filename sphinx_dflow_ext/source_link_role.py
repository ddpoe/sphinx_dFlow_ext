"""
Custom Sphinx role for source code links.

Provides the :source-link: role that generates links to browsable source
HTML with step-level anchors.
"""

from docutils import nodes
from sphinx.util import logging as sphinx_logging

logger = sphinx_logging.getLogger(__name__)


def _get_relative_prefix(inliner):
    """
    Calculate the relative path prefix to reach document root from current doc.
    
    For a document at 'cli/scan', we need '../' to reach the root.
    For a document at 'cli/subdir/page', we need '../../'.
    For a document at 'index', we need '' (empty - already at root).
    
    Args:
        inliner: The docutils inliner object containing document context
    
    Returns:
        String of '../' repeated for each directory level, or empty string
    """
    try:
        # Get the current document name (e.g., 'cli/scan', 'index')
        env = inliner.document.settings.env
        docname = env.docname  # e.g., 'cli/scan' or 'getting-started/quickstart'
        
        # Count directory separators to determine depth
        depth = docname.count('/')
        
        # Build the prefix: one '../' for each level of depth
        if depth > 0:
            return '../' * depth
        else:
            return ''
    except Exception as e:
        logger.debug(f"Could not determine document depth: {e}, using '../' as fallback")
        # Fallback to single '../' for backwards compatibility
        return '../'


def source_link_role(name, rawtext, text, lineno, inliner, options=None, content=None):
    """
    Role to create links to source code with step anchors.
    
    Usage:
        :source-link:`elastic_net_modules.data_loading#step-1`
        :source-link:`module_name#step-1.1`
    
    Args:
        name: Role name ('source-link')
        rawtext: Full role text including markup
        text: Role content (e.g., "elastic_net_modules.data_loading#step-1")
        lineno: Line number in source document
        inliner: Inliner object for creating nodes
        options: Options dict (optional)
        content: Content list (optional)
    
    Returns:
        Tuple of (nodes, messages)
    """
    if options is None:
        options = {}
    if content is None:
        content = []
    
    try:
        # Parse module#anchor format
        if '#' in text:
            module_part, anchor = text.split('#', 1)
        else:
            module_part = text
            anchor = ''
        
        # Convert module path to URL path
        # elastic_net_modules.data_loading -> _modules/elastic_net_modules/data_loading.html
        module_path = module_part.replace('.', '/').replace('\\', '/')
        
        # Calculate relative path based on current document depth
        prefix = _get_relative_prefix(inliner)
        
        # Build URL with correct relative path
        if anchor:
            url = f"{prefix}_modules/{module_path}.html#{anchor}"
        else:
            url = f"{prefix}_modules/{module_path}.html"
        
        # Create reference node with [source] text
        node = nodes.reference(
            rawtext, 
            '[source]',
            refuri=url,
            classes=['source-link', 'viewcode-link']
        )
        
        # Add title for hover text
        step_display = anchor.replace('step-', 'Step ').replace('-', '.') if anchor else module_part
        node['title'] = f"View source for {step_display}"
        
        return [node], []
        
    except Exception as e:
        logger.warning(f"Error parsing source-link '{text}': {e}")
        # Return plain text on error
        node = nodes.literal(rawtext, text)
        return [node], []


def source_line_role(name, rawtext, text, lineno, inliner, options=None, content=None):
    """
    Role to create links to specific source lines.
    
    Usage:
        :source-line:`elastic_net_modules.data_loading:45`
    
    Args:
        name: Role name ('source-line')
        rawtext: Full role text including markup
        text: Role content (e.g., "elastic_net_modules.data_loading:45")
        lineno: Line number in source document
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
    
    try:
        # Parse module:line_number format
        if ':' in text:
            module_part, line_str = text.rsplit(':', 1)
            line_num = int(line_str)
        else:
            logger.warning(f"source-line role expects 'module:line' format, got: {text}")
            return [nodes.literal(rawtext, text)], []
        
        # Convert module path to URL path
        module_path = module_part.replace('.', '/').replace('\\', '/')
        
        # Calculate relative path based on current document depth
        prefix = _get_relative_prefix(inliner)

        # Build URL with line anchor
        url = f"{prefix}_modules/{module_path}.html#line-{line_num}"
        
        # Create reference node
        node = nodes.reference(
            rawtext,
            f"[line {line_num}]",
            refuri=url,
            classes=['source-link', 'source-line-link']
        )
        
        node['title'] = f"View source at line {line_num}"
        
        return [node], []
        
    except ValueError as e:
        logger.warning(f"Invalid line number in source-line '{text}': {e}")
        return [nodes.literal(rawtext, text)], []
    except Exception as e:
        logger.warning(f"Error parsing source-line '{text}': {e}")
        return [nodes.literal(rawtext, text)], []


def step_source_role(name, rawtext, text, lineno, inliner, options=None, content=None):
    """
    Convenience role combining step reference with source link.
    
    Usage:
        :step-source:`1.1|elastic_net_modules.data_loading`
    
    Generates: Step 1.1 [source]
    
    Args:
        name: Role name
        rawtext: Full role text
        text: Role content
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
    
    try:
        # Parse step_num|module format
        if '|' in text:
            step_num, module_part = text.split('|', 1)
        else:
            logger.warning(f"step-source role expects 'step_num|module' format, got: {text}")
            return [nodes.literal(rawtext, text)], []
        
        # Create step reference text
        step_text = nodes.strong('', f"Step {step_num}")
        step_text['classes'].append('workflow-step-ref')
        
        # Create source link
        module_path = module_part.replace('.', '/').replace('\\', '/')
        anchor = f"step-{step_num.replace('.', '-')}"
        
        # Calculate relative path based on current document depth
        prefix = _get_relative_prefix(inliner)
        url = f"{prefix}_modules/{module_path}.html#{anchor}"
        
        source_link = nodes.reference(
            '',
            '[source]',
            refuri=url,
            classes=['source-link']
        )
        source_link['title'] = f"View source for Step {step_num}"
        
        # Create container
        container = nodes.inline('', '')
        container += step_text
        container += nodes.Text(' ')
        container += source_link
        
        return [container], []
        
    except Exception as e:
        logger.warning(f"Error parsing step-source '{text}': {e}")
        return [nodes.literal(rawtext, text)], []
