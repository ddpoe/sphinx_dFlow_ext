"""
Source HTML generator for workflow documentation.

Generates browsable HTML source files with syntax highlighting and
step anchors for direct linking from workflow documentation.

The generated source pages feature:
- 2-column layout: step navigation (left) + source code (right)
- Syntax highlighting via Pygments
- Step anchors for direct linking
- Line highlighting when navigating to steps
"""

from pathlib import Path
from typing import Dict, List, Optional, Set, Any
import logging
import html

try:
    from pygments import highlight
    from pygments.lexers import PythonLexer
    from pygments.formatters import HtmlFormatter
    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False

logger = logging.getLogger(__name__)


def collect_all_source_files(hierarchical_steps: List[Any]) -> Dict[str, Set[str]]:
    """
    Collect all unique source files referenced by workflow steps.
    
    Traverses the hierarchical step tree and collects source_file paths
    along with the step IDs and line numbers for each file.
    
    Args:
        hierarchical_steps: List of HierarchicalStep objects
    
    Returns:
        Dictionary mapping source_file path -> dict with 'module_name' and 'step_lines'
    """
    source_files: Dict[str, Dict] = {}
    
    def _collect_recursive(step: Any):
        source_file = getattr(step, 'source_file', None)
        source_module = getattr(step, 'source_module', None)
        source_line = getattr(step, 'source_line', None)
        step_num = getattr(step, 'hierarchical_number', getattr(step, 'number', ''))
        
        if source_file and source_line:
            if source_file not in source_files:
                source_files[source_file] = {
                    'module_name': source_module or Path(source_file).stem,
                    'step_lines': {}
                }
            
            # Add step -> line mapping
            step_id = f"step-{str(step_num).replace('.', '-')}"
            source_files[source_file]['step_lines'][step_id] = source_line
        
        # Recurse into children
        children = getattr(step, 'children', []) or getattr(step, 'sub_steps', [])
        for child in children:
            _collect_recursive(child)
    
    for step in hierarchical_steps:
        _collect_recursive(step)
    
    return source_files


class SourceHTMLGenerator:
    """Generate browsable HTML source files with step anchors."""
    
    def __init__(self, output_dir: Path, config: Optional[Dict] = None):
        """
        Initialize source HTML generator.
        
        Args:
            output_dir: Build output directory (e.g., _build/html)
            config: Optional configuration dict
        """
        self.output_dir = Path(output_dir)
        self.modules_dir = self.output_dir / '_modules'
        self.config = config or {}
        
    def generate_source_html(
        self, 
        module_path: Path,
        module_name: str,
        step_line_map: Optional[Dict[str, int]] = None,
        step_data: Optional[Dict[str, Dict]] = None,
        module_paths: Optional[Dict[str, str]] = None
    ) -> Optional[Path]:
        """
        Generate HTML source file with syntax highlighting and step anchors.
        
        Args:
            module_path: Path to Python source file
            module_name: Fully qualified module name (e.g., 'elastic_net_modules.data_loading')
            step_line_map: Mapping of step IDs to line numbers
                          e.g., {'step-1': 45, 'step-1.1': 52, 'step-2': 78}
            step_data: Full step data for navigation (optional)
                      e.g., {step_id: {'line': int, 'name': str, 'number': str, 'module': str}}
            module_paths: Mapping of module names to their HTML file paths for cross-linking
        
        Returns:
            Path to generated HTML file, or None if generation failed
        """
        if not module_path.exists():
            logger.warning(f"Source file not found: {module_path}")
            return None
        
        step_line_map = step_line_map or {}
        step_data = step_data or {}
        module_paths = module_paths or {}
        
        # Store current module name and paths for use in navigation building
        self._current_module = module_name
        self._module_paths = module_paths
        
        try:
            # Read source
            with open(module_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            # Generate HTML with syntax highlighting
            html_content = self._generate_highlighted_html(
                source, 
                module_name, 
                step_line_map,
                step_data
            )
            
            # Determine output path
            output_path = self._get_output_path(module_name)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write HTML file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"Generated source HTML: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error generating source HTML for {module_name}: {e}")
            return None
    
    def _get_output_path(self, module_name: str) -> Path:
        """Get output path for module source HTML."""
        # Convert module name to path: elastic_net_modules.data_loading -> elastic_net_modules/data_loading.html
        parts = module_name.split('.')
        return self.modules_dir / '/'.join(parts[:-1]) / f"{parts[-1]}.html" if len(parts) > 1 else self.modules_dir / f"{parts[0]}.html"
    
    def _generate_highlighted_html(
        self, 
        source: str, 
        module_name: str,
        step_line_map: Dict[str, int],
        step_data: Optional[Dict[str, Dict]] = None
    ) -> str:
        """
        Generate HTML with syntax highlighting and step anchors.
        
        Args:
            source: Python source code
            module_name: Module name for title
            step_line_map: Step ID to line number mapping
            step_data: Full step data for navigation
        
        Returns:
            Complete HTML document
        """
        step_data = step_data or {}
        
        # Create reverse mapping: line_number -> step_id
        line_to_step = {line: step_id for step_id, line in step_line_map.items()}
        
        if PYGMENTS_AVAILABLE:
            # Use Pygments for syntax highlighting
            html_lines = self._highlight_with_pygments(source, line_to_step)
        else:
            # Fallback: basic HTML escaping
            html_lines = self._basic_highlight(source, line_to_step)
        
        # Build complete HTML document
        return self._build_html_document(module_name, html_lines, step_line_map, step_data)
    
    def _highlight_with_pygments(
        self, 
        source: str, 
        line_to_step: Dict[int, str]
    ) -> List[str]:
        """
        Generate syntax-highlighted HTML lines using Pygments.
        
        Args:
            source: Python source code
            line_to_step: Line number to step ID mapping
        
        Returns:
            List of HTML lines
        """
        lexer = PythonLexer()
        formatter = HtmlFormatter(
            linenos=True,
            linenostart=1,
            cssclass='source',
            anchorlinenos=True,
            lineanchors='line'
        )
        
        # Generate highlighted HTML
        highlighted = highlight(source, lexer, formatter)
        
        # Inject step anchors into the HTML
        html_lines = highlighted.split('\n')
        result_lines = []
        
        for i, line in enumerate(html_lines, 1):
            if i in line_to_step:
                step_id = line_to_step[i]
                # Add step anchor span before the line
                anchor = f'<span id="{step_id}" class="step-anchor"></span>'
                line = anchor + line
            result_lines.append(line)
        
        return result_lines
    
    def _basic_highlight(
        self, 
        source: str, 
        line_to_step: Dict[int, str]
    ) -> List[str]:
        """
        Generate basic HTML without Pygments (fallback).
        
        Args:
            source: Python source code  
            line_to_step: Line number to step ID mapping
        
        Returns:
            List of HTML lines
        """
        lines = source.split('\n')
        html_lines = []
        
        for i, line in enumerate(lines, 1):
            escaped = html.escape(line)
            line_id = f'line-{i}'
            
            # Add step anchor if this line has a step marker
            anchor = ''
            css_class = 'line'
            if i in line_to_step:
                step_id = line_to_step[i]
                anchor = f'<span id="{step_id}" class="step-anchor"></span>'
                css_class += ' step-line'
            
            html_line = f'{anchor}<span id="{line_id}" class="{css_class}"><span class="lineno">{i:4d}</span> <code>{escaped}</code></span>'
            html_lines.append(html_line)
        
        return html_lines
    
    def _build_html_document(
        self, 
        module_name: str, 
        html_lines: List[str],
        step_line_map: Dict[str, int],
        step_data: Optional[Dict[str, Dict]] = None
    ) -> str:
        """
        Build complete HTML document with 2-column layout.
        
        Layout:
        - Left column (250px): Step navigation with links
        - Right column (remaining): Syntax-highlighted source code
        
        Args:
            module_name: Module name for title
            html_lines: Highlighted HTML lines
            step_line_map: Step ID to line number mapping
            step_data: Full step data for navigation
        
        Returns:
            Complete HTML document string
        """
        step_data = step_data or {}
        
        # Get Pygments CSS if available
        pygments_css = ""
        if PYGMENTS_AVAILABLE:
            formatter = HtmlFormatter()
            pygments_css = formatter.get_style_defs('.source')
        
        # Build step navigation items - use step_data if available, else convert from step_line_map
        if step_data:
            step_nav_items = self._build_step_navigation_items(step_data)
        else:
            # Convert step_line_map to step_data format for backward compat
            legacy_data = {
                sid: {'line': line, 'name': '', 'number': sid.replace('step-', '').replace('-', '.'), 'module': module_name}
                for sid, line in step_line_map.items()
            }
            step_nav_items = self._build_step_navigation_items(legacy_data)
        
        content = '\n'.join(html_lines)
        
        # Calculate relative path to _static based on module depth
        module_depth = module_name.count('.') + 1
        static_prefix = '../' * module_depth
        
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Source: {module_name}</title>
    <style>
        {pygments_css}
        
        * {{
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0;
            padding: 0;
            background: #fafafa;
            height: 100vh;
            overflow: hidden;
        }}
        
        /* Header bar */
        .source-header {{
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 12px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 100;
            height: 50px;
        }}
        
        .source-header h1 {{
            margin: 0;
            font-size: 1.1em;
            font-weight: 500;
        }}
        
        .source-header .module-path {{
            color: #bdc3c7;
            font-family: monospace;
            font-size: 0.9em;
        }}
        
        .back-link {{
            color: #3498db;
            text-decoration: none;
            font-size: 0.9em;
            padding: 6px 12px;
            background: rgba(255,255,255,0.1);
            border-radius: 4px;
            transition: background 0.2s;
        }}
        
        .back-link:hover {{
            background: rgba(255,255,255,0.2);
            color: white;
        }}
        
        /* Main 2-column layout */
        .main-container {{
            display: flex;
            margin-top: 50px;
            height: calc(100vh - 50px);
        }}
        
        /* Left column - Step Navigation */
        .step-nav-column {{
            width: 350px;
            min-width: 350px;
            background: #fff;
            border-right: 1px solid #e0e0e0;
            overflow-y: auto;
            padding: 15px;
        }}
        
        .step-nav-header {{
            font-size: 0.85em;
            font-weight: 600;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 2px solid #3498db;
        }}
        
        .step-nav-list {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        
        .step-nav-list li {{
            margin: 0;
        }}
        
        .step-nav-list a {{
            display: block;
            padding: 8px 12px;
            color: #333;
            text-decoration: none;
            border-radius: 4px;
            font-size: 0.9em;
            transition: all 0.15s;
            border-left: 3px solid transparent;
        }}
        
        .step-nav-list a:hover {{
            background: #e3f2fd;
            color: #1976d2;
            border-left-color: #1976d2;
        }}
        
        .step-nav-list a.active {{
            background: #bbdefb;
            color: #0d47a1;
            border-left-color: #0d47a1;
            font-weight: 500;
        }}
        
        .step-nav-list .step-number {{
            display: block;
            font-size: 0.75em;
            color: #666;
            font-weight: 600;
            letter-spacing: 0.3px;
        }}
        
        .step-nav-list .step-name {{
            display: block;
            font-weight: 500;
            margin-top: 2px;
            line-height: 1.3;
        }}
        
        .step-nav-list .step-meta {{
            display: flex;
            justify-content: space-between;
            margin-top: 4px;
            font-size: 0.75em;
            color: #888;
        }}
        
        .step-nav-list .step-module {{
            font-style: italic;
            color: #2196f3;
        }}
        
        .step-nav-list .step-line {{
            font-family: monospace;
            color: #888;
        }}
        
        /* Hierarchical step navigation */
        .step-nav-list .step-parent {{
            margin-bottom: 2px;
            width: 100%;
        }}
        
        .step-nav-list .step-parent-header {{
            display: flex;
            align-items: flex-start;
            width: 100%;
        }}
        
        .step-nav-list .step-parent-header > a {{
            flex: 1;
            width: 100%;
        }}
        
        .step-nav-list .toggle-btn {{
            background: none;
            border: none;
            cursor: pointer;
            padding: 6px 6px 6px 0;
            font-size: 0.7em;
            color: #666;
            transition: transform 0.2s;
            flex-shrink: 0;
            width: 18px;
        }}
        
        .step-nav-list .toggle-btn:hover {{
            color: #1976d2;
        }}
        
        .step-nav-list .toggle-btn.collapsed {{
            transform: rotate(-90deg);
        }}
        
        .step-nav-list .substeps {{
            list-style: none;
            padding-left: 20px;
            margin: 0;
            overflow: hidden;
            transition: max-height 0.3s ease-out;
            width: 100%;
        }}
        
        .step-nav-list .substeps.collapsed {{
            max-height: 0 !important;
        }}
        
        .step-nav-list .substeps li {{
            width: 100%;
        }}
        
        .step-nav-list .substeps li a {{
            padding: 5px 10px;
            font-size: 0.85em;
            border-left: 2px solid #e0e0e0;
            margin-left: 4px;
            width: 100%;
            box-sizing: border-box;
        }}
        
        .step-nav-list .substeps li a:hover {{
            border-left-color: #1976d2;
        }}
        
        /* Step dividers between major steps */
        .step-divider {{
            border: none;
            border-top: 1px solid #e0e0e0;
            margin: 10px 0;
        }}
        
        /* Right column - Source Code */
        .source-column {{
            flex: 1;
            overflow: auto;
            background: #fff;
        }}
        
        .source-container {{
            min-width: 100%;
        }}
        
        .source {{
            font-family: "SF Mono", "Monaco", "Inconsolata", "Fira Mono", "Consolas", monospace;
            font-size: 13px;
            line-height: 1.6;
            padding: 0;
            margin: 0;
        }}
        
        /* Line styling */
        .line {{
            display: block;
            padding: 0 15px 0 0;
            white-space: pre;
            min-height: 1.6em;
        }}
        
        .lineno {{
            display: inline-block;
            width: 50px;
            color: #999;
            text-align: right;
            padding-right: 15px;
            margin-right: 15px;
            border-right: 1px solid #eee;
            user-select: none;
            background: #fafafa;
        }}
        
        /* Step anchor and highlighting */
        .step-anchor {{
            display: block;
            height: 0;
            position: relative;
            scroll-margin-top: 70px;
        }}
        
        /* Scroll offset for line anchors */
        .line, [id^="line-"] {{
            scroll-margin-top: 70px;
        }}
        
        /* Highlighted step line */
        .step-line {{
            background: #fffde7;
        }}
        
        .step-line .lineno {{
            background: #fff9c4;
            color: #f57f17;
            font-weight: 600;
        }}
        
        /* Target highlighting (when navigating to anchor) */
        :target,
        .step-anchor:target + .line,
        .line:target {{
            background: #fff59d !important;
            animation: highlight-flash 2s ease-out;
        }}
        
        :target .lineno,
        .step-anchor:target + .line .lineno {{
            background: #ffee58 !important;
            color: #e65100 !important;
        }}
        
        @keyframes highlight-flash {{
            0% {{ background: #ffeb3b; }}
            100% {{ background: #fff59d; }}
        }}
        
        /* Clicked/active line highlighting */
        .line.highlighted {{
            background: #fff59d !important;
            animation: highlight-flash 2s ease-out;
        }}
        
        .line.highlighted .lineno {{
            background: #ffee58 !important;
            color: #e65100 !important;
        }}
        
        /* Highlight for Pygments table layout */
        .highlighted,
        tr.highlighted,
        td.highlighted,
        span.highlighted {{
            background: #fff59d !important;
            animation: highlight-flash 2s ease-out;
        }}
        
        /* Highlight the entire source table row */
        .source tr.highlighted td {{
            background: #fff59d !important;
        }}
        
        .source tr.highlighted td.linenos {{
            background: #ffee58 !important;
        }}
        
        /* No steps message */
        .no-steps-message {{
            padding: 20px;
            color: #666;
            font-style: italic;
            text-align: center;
        }}
        
        /* Responsive - collapse nav on small screens */
        @media (max-width: 768px) {{
            .step-nav-column {{
                display: none;
            }}
        }}
    </style>
    <script>
        // Highlight active step in navigation and source line when clicking
        document.addEventListener('DOMContentLoaded', function() {{
            const navLinks = document.querySelectorAll('.step-nav-list a[href^="#"]');
            const toggleBtns = document.querySelectorAll('.toggle-btn');
            let highlightedLine = null;
            
            // Toggle collapse/expand for substeps
            toggleBtns.forEach(btn => {{
                btn.addEventListener('click', function(e) {{
                    e.stopPropagation();
                    const substeps = this.closest('.step-parent').querySelector('.substeps');
                    if (substeps) {{
                        this.classList.toggle('collapsed');
                        substeps.classList.toggle('collapsed');
                    }}
                }});
            }});
            
            // Function to highlight a source line
            function highlightSourceLine(stepId) {{
                // Remove previous highlight
                if (highlightedLine) {{
                    highlightedLine.classList.remove('highlighted');
                }}
                
                // Find the step anchor
                const anchor = document.getElementById(stepId);
                if (!anchor) return;
                
                // Strategy 1: Look for Pygments line structure
                // Pygments creates: <span id="line-N"> containing a link <a href="#line-N">
                // The actual line content is in the same container or sibling
                
                // Try to find the parent table row or line container
                let lineElement = anchor.closest('tr, .line, pre > span');
                
                // Strategy 2: If anchor is step-anchor class, find associated line
                if (!lineElement && anchor.classList.contains('step-anchor')) {{
                    // Look at parent or next sibling
                    lineElement = anchor.parentElement;
                    if (lineElement && lineElement.tagName === 'PRE') {{
                        // Find by scrolling to anchor position
                        lineElement = null;
                    }}
                }}
                
                // Strategy 3: For Pygments table layout, find the linenos anchor
                if (!lineElement) {{
                    // Look for the line number link that Pygments generates
                    const allLineAnchors = document.querySelectorAll('a[href^="#line-"]');
                    for (const la of allLineAnchors) {{
                        if (la.closest('td, span') && la.textContent.trim()) {{
                            const lineNum = parseInt(la.textContent.trim());
                            // Check if this line number matches what we're looking for
                            // We need to get the line number from step data
                            const tr = la.closest('tr');
                            if (tr) {{
                                const cells = tr.querySelectorAll('td');
                                if (cells.length >= 2) {{
                                    lineElement = cells[1]; // Code cell
                                    break;
                                }}
                            }}
                        }}
                    }}
                }}
                
                // Strategy 4: Highlight by adding a visible marker
                if (lineElement) {{
                    lineElement.classList.add('highlighted');
                    highlightedLine = lineElement;
                }} else {{
                    // Fallback: add a highlight effect to the anchor's parent container
                    const container = anchor.parentElement;
                    if (container) {{
                        container.classList.add('highlighted');
                        highlightedLine = container;
                    }}
                }}
            }}
            
            // Handle click to highlight nav item and source line
            navLinks.forEach(link => {{
                link.addEventListener('click', function(e) {{
                    // Remove active from all
                    navLinks.forEach(l => l.classList.remove('active'));
                    // Add active to clicked
                    this.classList.add('active');
                    
                    // Highlight the target source line
                    const stepId = this.getAttribute('href').substring(1);
                    setTimeout(() => highlightSourceLine(stepId), 100);
                }});
            }});
            
            // Check hash on load and highlight
            if (window.location.hash) {{
                const hash = window.location.hash;
                const activeLink = document.querySelector(`.step-nav-list a[href="${{hash}}"]`);
                if (activeLink) {{
                    activeLink.classList.add('active');
                    // Expand ALL parent containers up the tree
                    let parent = activeLink.closest('.substeps');
                    while (parent) {{
                        parent.classList.remove('collapsed');
                        const header = parent.previousElementSibling;
                        if (header) {{
                            const toggleBtn = header.querySelector('.toggle-btn');
                            if (toggleBtn) toggleBtn.classList.remove('collapsed');
                        }}
                        parent = parent.parentElement?.closest('.substeps');
                    }}
                }}
                setTimeout(() => highlightSourceLine(hash.substring(1)), 200);
            }}
            
            // Handle hash change
            window.addEventListener('hashchange', function() {{
                navLinks.forEach(l => l.classList.remove('active'));
                const hash = window.location.hash;
                const activeLink = document.querySelector(`.step-nav-list a[href="${{hash}}"]`);
                if (activeLink) {{
                    activeLink.classList.add('active');
                }}
                highlightSourceLine(hash.substring(1));
            }});
        }});
    </script>
</head>
<body>
    <div class="source-header">
        <div>
            <h1>Source Code</h1>
            <span class="module-path">{module_name}</span>
        </div>
        <a href="javascript:history.back()" class="back-link">← Back to Documentation</a>
    </div>
    
    <div class="main-container">
        <div class="step-nav-column">
            <div class="step-nav-header">Workflow Steps</div>
            {step_nav_items}
        </div>
        
        <div class="source-column">
            <div class="source-container">
                <div class="source">
{content}
                </div>
            </div>
        </div>
    </div>
</body>
</html>'''
    
    def _build_step_navigation_items(self, step_data: Dict[str, Dict]) -> str:
        """
        Build hierarchical HTML list items for step navigation.
        
        Generates deeply nested lists with toggles at every level that has children.
        Supports arbitrary nesting depth (1, 1.1, 1.1.1, 1.1.1.1, etc.)
        
        Args:
            step_data: Step ID to step info mapping
                      e.g., {step_id: {'line': int, 'name': str, 'number': str, 'module': str}}
        
        Returns:
            HTML string for step navigation list
        """
        if not step_data:
            return '<p class="no-steps-message">No workflow steps in this module</p>'
        
        def parse_step_number(num_str: str) -> tuple:
            """Parse step number string into tuple for hierarchical sorting.
            E.g., '1.2.3' -> (1, 2, 3), '2' -> (2,)
            """
            try:
                return tuple(int(p) for p in num_str.split('.') if p)
            except (ValueError, AttributeError):
                return (999,)  # Put unparseable at end
        
        def get_depth(num_str: str) -> int:
            """Get nesting depth. '1' -> 0, '1.2' -> 1, '1.2.3' -> 2."""
            return str(num_str).count('.')
        
        def get_parent_number(num_str: str) -> str:
            """Get parent step number. E.g., '1.2.3' -> '1.2', '1.2' -> '1', '1' -> ''."""
            parts = str(num_str).rsplit('.', 1)
            return parts[0] if len(parts) > 1 else ''
        
        def get_top_level_number(num_str: str) -> str:
            """Get top-level step number. E.g., '1.2.3' -> '1', '2' -> '2'."""
            return str(num_str).split('.')[0]
        
        # Get current module and module paths for cross-linking
        current_module = getattr(self, '_current_module', '')
        module_paths = getattr(self, '_module_paths', {})
        
        def get_relative_path_to_module(from_module: str, to_module: str) -> str:
            """Calculate relative path from one module's HTML to another."""
            if from_module == to_module:
                return ''  # Same file, just use anchor
            
            from_parts = from_module.split('.')
            to_parts = to_module.split('.')
            
            # Calculate how many levels up we need to go
            from_depth = len(from_parts) - 1  # -1 because the last part is the filename
            
            # Build the relative path
            up_path = '../' * from_depth if from_depth > 0 else ''
            
            # Build path to target module
            if len(to_parts) > 1:
                to_path = '/'.join(to_parts[:-1]) + '/' + to_parts[-1] + '.html'
            else:
                to_path = to_parts[0] + '.html'
            
            return up_path + to_path
        
        def build_step_link(step_id: str, info: dict) -> str:
            """Build HTML for a single step link with cross-file linking."""
            step_number = info.get('number', '')
            step_name = info.get('name', '')
            step_module = info.get('source_module', info.get('module', ''))
            line_num = info.get('line', 0)
            module_display = step_module.split('.')[-1] if step_module else ''
            
            # Determine if this is a cross-file link
            if step_module and step_module != current_module:
                # Cross-file link
                relative_path = get_relative_path_to_module(current_module, step_module)
                href = f'{relative_path}#{step_id}'
                external_indicator = ' ↗'
            else:
                # Same-file anchor link
                href = f'#{step_id}'
                external_indicator = ''
            
            return f'''<a href="{href}">
                    <span class="step-number">Step {step_number}</span>
                    <span class="step-name">{step_name}{external_indicator}</span>
                    <span class="step-meta">
                        <span class="step-module">{module_display}</span>
                        <span class="step-line">L{line_num}</span>
                    </span>
                </a>'''
        
        # Build a tree structure
        # Each node: {'step_id': str, 'info': dict, 'children': [nodes]}
        class TreeNode:
            def __init__(self, step_id: str = None, info: dict = None):
                self.step_id = step_id
                self.info = info or {}
                self.children = []
                self.number = info.get('number', '') if info else ''
        
        # Sort steps by hierarchical step number
        sorted_steps = sorted(
            step_data.items(), 
            key=lambda x: parse_step_number(x[1].get('number', '999'))
        )
        
        # Build tree by inserting each step into the right place
        root = TreeNode()  # Virtual root
        nodes_by_number = {'': root}  # Map step number -> node
        
        def find_nearest_ancestor(step_number: str) -> TreeNode:
            """Find the nearest existing ancestor node for a step number.
            E.g., for '1.3.1.1', try '1.3.1', then '1.3', then '1', then root.
            """
            current = step_number
            while current:
                parent_num = get_parent_number(current)
                if parent_num in nodes_by_number:
                    return nodes_by_number[parent_num]
                current = parent_num
            return root
        
        for step_id, info in sorted_steps:
            step_number = info.get('number', '')
            node = TreeNode(step_id, info)
            nodes_by_number[step_number] = node
            
            # Find nearest existing ancestor
            parent_node = find_nearest_ancestor(step_number)
            parent_node.children.append(node)
        
        def render_node(node: TreeNode, depth: int = 0, is_top_level: bool = False) -> str:
            """Recursively render a node and its children."""
            indent = '    ' * (depth + 3)
            
            if node.step_id is None:
                # Root node - just render children
                return ''
            
            has_children = len(node.children) > 0
            step_link = build_step_link(node.step_id, node.info)
            
            if has_children:
                # Render children recursively
                children_html = []
                for child in node.children:
                    children_html.append(render_node(child, depth + 1))
                children_content = '\n'.join(children_html)
                
                return f'''{indent}<li class="step-parent">
{indent}    <div class="step-parent-header">
{indent}        <button class="toggle-btn collapsed" title="Toggle substeps">▼</button>
{indent}        {step_link}
{indent}    </div>
{indent}    <ul class="substeps collapsed">
{children_content}
{indent}    </ul>
{indent}</li>'''
            else:
                # Leaf node - no toggle
                return f'''{indent}<li class="step-parent">
{indent}    <div class="step-parent-header">
{indent}        {step_link}
{indent}    </div>
{indent}</li>'''
        
        # Render top-level items with dividers between them
        items = []
        for i, child in enumerate(root.children):
            if i > 0:
                # Add divider between top-level steps
                items.append('            <hr class="step-divider"/>')
            items.append(render_node(child, depth=0, is_top_level=True))
        
        return f'''<ul class="step-nav-list">
{chr(10).join(items)}
            </ul>'''


def generate_all_source_pages(app, exception):
    """
    Sphinx event handler to generate source pages after build.
    
    This function is connected to the 'build-finished' event and generates
    browsable source HTML for ALL documented modules referenced in the workflow.
    
    Args:
        app: Sphinx application
        exception: Exception if build failed
    """
    if exception:
        logger.info("Skipping source generation due to build exception")
        return
    
    # Get tracked modules from app environment
    env = app.env
    if not hasattr(env, 'workflow_source_mappings'):
        logger.info("No workflow source mappings found - source pages not generated")
        return
    
    mappings = env.workflow_source_mappings
    logger.info(f"Generating source pages for {len(mappings)} module(s)")
    
    # Merge ALL step data from all modules for the unified navigation
    all_step_data = {}
    module_paths = {}  # Map module_name -> output path for cross-linking
    
    for module_name, mapping_data in mappings.items():
        step_data = mapping_data.get('steps', {})
        # Add source_file info to each step for cross-module linking
        for step_id, info in step_data.items():
            info['source_module'] = module_name
        all_step_data.update(step_data)
        
        # Calculate the relative path for this module
        parts = module_name.split('.')
        if len(parts) > 1:
            module_paths[module_name] = '/'.join(parts[:-1]) + '/' + parts[-1] + '.html'
        else:
            module_paths[module_name] = parts[0] + '.html'
    
    generator = SourceHTMLGenerator(Path(app.outdir))
    generated_count = 0
    
    for module_name, mapping_data in mappings.items():
        source_path = mapping_data.get('source_path', '')
        step_data = mapping_data.get('steps', {})
        
        # Convert step_data to step_line_map for backward compatibility
        # step_data format: {step_id: {'line': int, 'name': str, 'number': str, 'module': str}}
        step_line_map = {sid: info.get('line', 0) for sid, info in step_data.items()}
        
        if not source_path:
            logger.warning(f"  Module '{module_name}': No source path - skipping")
            continue
        
        module_path = Path(source_path)
        
        logger.info(f"  Module: {module_name}")
        logger.info(f"    Source: {module_path}")
        logger.info(f"    Steps (this module): {len(step_data)}")
        logger.info(f"    Steps (all modules): {len(all_step_data)}")
        
        if module_path.exists():
            result = generator.generate_source_html(
                module_path,
                module_name,
                step_line_map,
                all_step_data,  # Pass ALL step data for unified navigation
                module_paths   # Pass module path mappings for cross-linking
            )
            if result:
                logger.info(f"    Generated: {result}")
                generated_count += 1
        else:
            logger.warning(f"    Source file not found: {module_path}")
    
    logger.info(f"Source page generation complete: {generated_count}/{len(mappings)} modules")
