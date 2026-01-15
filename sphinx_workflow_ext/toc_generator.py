"""
Table of Contents generator for workflow documentation.

Generates a navigable sidebar TOC from discovered workflows,
organized by package with expandable tier lists.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

from docutils import nodes
from docutils.statemachine import StringList

from .discovery import DiscoveredWorkflow, DiscoveryResult

logger = logging.getLogger(__name__)


class WorkflowTOCGenerator:
    """
    Generate table of contents for workflow documentation.
    
    Creates structured navigation with:
    - Package grouping
    - Module listings
    - Tier sub-items
    - Links to generated documentation pages
    """
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize TOC generator.
        
        Args:
            config: Configuration options:
                - show_tier_counts: Show number of tiers per module
                - expand_packages: Start with packages expanded
                - show_descriptions: Show module docstring summaries
                - group_by_package: Group modules by package (vs flat list)
        """
        self.config = config or {}
        self.show_tier_counts = self.config.get('show_tier_counts', True)
        self.expand_packages = self.config.get('expand_packages', True)
        self.show_descriptions = self.config.get('show_descriptions', False)
        self.group_by_package = self.config.get('group_by_package', True)
    
    def generate_rst_toc(
        self,
        discovery_result: DiscoveryResult,
        current_page: Optional[str] = None
    ) -> List[str]:
        """
        Generate RST lines for a workflow TOC.
        
        Args:
            discovery_result: Result from WorkflowDiscovery.
            current_page: Current page path (for highlighting).
        
        Returns:
            List of RST lines.
        """
        lines = []
        
        if not discovery_result.workflows:
            lines.append("*No workflows discovered*")
            return lines
        
        if self.group_by_package:
            lines.extend(self._generate_grouped_toc(discovery_result, current_page))
        else:
            lines.extend(self._generate_flat_toc(discovery_result, current_page))
        
        return lines
    
    def _generate_grouped_toc(
        self,
        result: DiscoveryResult,
        current_page: Optional[str]
    ) -> List[str]:
        """Generate TOC grouped by package."""
        lines = []
        
        modules_by_package = result.modules_by_package
        
        for package_name in sorted(modules_by_package.keys()):
            modules = modules_by_package[package_name]
            
            # Package header
            display_package = package_name if package_name != "_root" else "Root Modules"
            lines.append(f"**{display_package}**")
            lines.append("")
            
            # Generate toctree for this package
            lines.append(".. toctree::")
            lines.append("   :maxdepth: 2")
            lines.append("")
            
            for workflow in modules:
                # Create link to workflow page
                page_name = self._get_page_name(workflow)
                display_name = workflow.module_name
                
                if self.show_tier_counts and workflow.has_tiers:
                    display_name += f" ({len(workflow.declared_tiers)} tiers)"
                
                lines.append(f"   {display_name} <{page_name}>")
            
            lines.append("")
        
        return lines
    
    def _generate_flat_toc(
        self,
        result: DiscoveryResult,
        current_page: Optional[str]
    ) -> List[str]:
        """Generate flat TOC (no package grouping)."""
        lines = []
        
        lines.append(".. toctree::")
        lines.append("   :maxdepth: 2")
        lines.append("")
        
        # Sort all workflows by display name
        all_workflows = sorted(result.workflows.values(), key=lambda w: w.display_name)
        
        for workflow in all_workflows:
            page_name = self._get_page_name(workflow)
            display_name = workflow.display_name
            
            if self.show_tier_counts and workflow.has_tiers:
                display_name += f" ({len(workflow.declared_tiers)} tiers)"
            
            lines.append(f"   {display_name} <{page_name}>")
        
        lines.append("")
        
        return lines
    
    def generate_sidebar_html(
        self,
        discovery_result: DiscoveryResult,
        current_module: Optional[str] = None,
        current_tier: Optional[str] = None
    ) -> str:
        """
        Generate HTML for sidebar navigation.
        
        Creates a collapsible tree structure with JavaScript interactivity.
        
        Args:
            discovery_result: Result from WorkflowDiscovery.
            current_module: Currently viewed module path.
            current_tier: Currently viewed tier name.
        
        Returns:
            HTML string for sidebar content.
        """
        if not discovery_result.workflows:
            return '<div class="workflow-toc-empty">No workflows discovered</div>'
        
        html_parts = ['<nav class="workflow-toc">']
        
        modules_by_package = discovery_result.modules_by_package
        
        for package_name in sorted(modules_by_package.keys()):
            modules = modules_by_package[package_name]
            display_package = package_name if package_name != "_root" else "📁 Root"
            
            # Package container
            expanded_class = "expanded" if self.expand_packages else ""
            html_parts.append(f'<div class="workflow-package {expanded_class}">')
            html_parts.append(f'<div class="package-header" onclick="togglePackage(this)">')
            html_parts.append(f'<span class="toggle-icon">{"▼" if self.expand_packages else "▶"}</span>')
            html_parts.append(f'<span class="package-name">📁 {display_package}</span>')
            html_parts.append('</div>')
            
            # Module list
            display_style = '' if self.expand_packages else 'style="display: none;"'
            html_parts.append(f'<ul class="module-list" {display_style}>')
            
            for workflow in modules:
                is_current = str(workflow.module_path) == current_module
                current_class = "current" if is_current else ""
                
                html_parts.append(f'<li class="workflow-module {current_class}">')
                
                if workflow.has_tiers and len(workflow.declared_tiers) > 1:
                    # Module with multiple tiers - collapsible
                    html_parts.append('<div class="module-header" onclick="toggleModule(this)">')
                    html_parts.append('<span class="toggle-icon">▶</span>')
                    html_parts.append(f'<span class="module-name">📄 {workflow.module_name}</span>')
                    html_parts.append('</div>')
                    
                    # Tier list
                    html_parts.append('<ul class="tier-list" style="display: none;">')
                    for tier in workflow.declared_tiers:
                        tier_current = current_tier == tier if is_current else False
                        tier_class = "current" if tier_current else ""
                        page_url = self._get_tier_url(workflow, tier)
                        html_parts.append(f'<li class="tier-item {tier_class}">')
                        html_parts.append(f'<a href="{page_url}">{tier}</a>')
                        html_parts.append('</li>')
                    html_parts.append('</ul>')
                else:
                    # Single tier or no tiers - direct link
                    tier = workflow.declared_tiers[0] if workflow.declared_tiers else 'default'
                    page_url = self._get_tier_url(workflow, tier)
                    html_parts.append(f'<a href="{page_url}" class="module-link">')
                    html_parts.append(f'<span class="module-name">📄 {workflow.module_name}</span>')
                    html_parts.append('</a>')
                
                html_parts.append('</li>')
            
            html_parts.append('</ul>')
            html_parts.append('</div>')
        
        html_parts.append('</nav>')
        
        return '\n'.join(html_parts)
    
    def generate_index_page_rst(
        self,
        discovery_result: DiscoveryResult,
        title: str = "Workflow Documentation",
        intro: Optional[str] = None
    ) -> List[str]:
        """
        Generate complete RST for a workflow index page.
        
        Args:
            discovery_result: Result from WorkflowDiscovery.
            title: Page title.
            intro: Optional introductory text.
        
        Returns:
            List of RST lines for the index page.
        """
        lines = []
        
        # Title
        lines.append(title)
        lines.append("=" * len(title))
        lines.append("")
        
        # Introduction
        if intro:
            lines.append(intro)
            lines.append("")
        
        # Summary section
        total_modules = len(discovery_result.workflows)
        all_tiers = discovery_result.get_all_tiers()
        
        lines.append(".. admonition:: Summary")
        lines.append("")
        lines.append(f"   - **Modules**: {total_modules}")
        lines.append(f"   - **Unique Tiers**: {', '.join(sorted(all_tiers)) if all_tiers else 'default'}")
        lines.append("")
        
        # Quick links by package
        modules_by_package = discovery_result.modules_by_package
        
        for package_name in sorted(modules_by_package.keys()):
            modules = modules_by_package[package_name]
            display_package = package_name if package_name != "_root" else "Root Modules"
            
            lines.append(f"{display_package}")
            lines.append("-" * len(display_package))
            lines.append("")
            
            for workflow in modules:
                # Module entry with tier links
                lines.append(f"**{workflow.module_name}**")
                
                if workflow.docstring:
                    lines.append(f"   {workflow.docstring}")
                
                lines.append("")
                
                # Tier links
                if workflow.has_tiers:
                    tier_links = []
                    for tier in workflow.declared_tiers:
                        page_ref = self._get_page_name(workflow, tier)
                        tier_links.append(f":doc:`{tier} <{page_ref}>`")
                    
                    lines.append("   *Tiers:* " + " | ".join(tier_links))
                    lines.append("")
        
        # Add toctree (hidden) for navigation
        lines.append(".. toctree::")
        lines.append("   :hidden:")
        lines.append("   :maxdepth: 2")
        lines.append("")
        
        for workflow in discovery_result.workflows.values():
            page_name = self._get_page_name(workflow)
            lines.append(f"   {page_name}")
        
        lines.append("")
        
        return lines
    
    def _get_page_name(
        self,
        workflow: DiscoveredWorkflow,
        tier: Optional[str] = None
    ) -> str:
        """Get the documentation page name/path for a workflow."""
        # Create a slug from module display name
        base_name = workflow.display_name.replace('.', '_')
        
        if tier:
            return f"workflows/{base_name}_{tier}"
        
        return f"workflows/{base_name}"
    
    def _get_tier_url(
        self,
        workflow: DiscoveredWorkflow,
        tier: str
    ) -> str:
        """Get URL for a specific tier page."""
        page_name = self._get_page_name(workflow, tier)
        return f"{page_name}.html"


class WorkflowIndexBuilder:
    """
    Build complete workflow index and individual tier pages.
    
    Integrates with Sphinx to generate documentation structure.
    """
    
    def __init__(
        self,
        discovery_result: DiscoveryResult,
        output_dir: Path,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize index builder.
        
        Args:
            discovery_result: Discovered workflows.
            output_dir: Directory for generated RST files.
            config: Configuration options.
        """
        self.result = discovery_result
        self.output_dir = output_dir
        self.config = config or {}
        self.toc_generator = WorkflowTOCGenerator(config)
    
    def build_all(self) -> List[Path]:
        """
        Build all index and tier pages.
        
        Returns:
            List of generated file paths.
        """
        generated_files = []
        
        # Ensure output directories exist
        workflows_dir = self.output_dir / 'workflows'
        workflows_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate main index page
        index_path = self._generate_index_page()
        generated_files.append(index_path)
        
        # Generate individual tier pages
        for workflow in self.result.workflows.values():
            tier_paths = self._generate_tier_pages(workflow, workflows_dir)
            generated_files.extend(tier_paths)
        
        return generated_files
    
    def _generate_index_page(self) -> Path:
        """Generate the main workflow index page."""
        lines = self.toc_generator.generate_index_page_rst(
            self.result,
            title="Workflow Documentation",
            intro="Auto-discovered workflow documentation organized by module and tier."
        )
        
        index_path = self.output_dir / 'workflow_index.rst'
        index_path.write_text('\n'.join(lines), encoding='utf-8')
        
        logger.info(f"Generated workflow index: {index_path}")
        return index_path
    
    def _generate_tier_pages(
        self,
        workflow: DiscoveredWorkflow,
        output_dir: Path
    ) -> List[Path]:
        """Generate pages for each tier of a workflow module."""
        generated = []
        
        for tier in workflow.declared_tiers:
            lines = self._generate_tier_page_rst(workflow, tier)
            
            page_name = f"{workflow.display_name.replace('.', '_')}_{tier}.rst"
            page_path = output_dir / page_name
            page_path.write_text('\n'.join(lines), encoding='utf-8')
            
            logger.info(f"Generated tier page: {page_path}")
            generated.append(page_path)
        
        return generated
    
    def _generate_tier_page_rst(
        self,
        workflow: DiscoveredWorkflow,
        tier: str
    ) -> List[str]:
        """Generate RST content for a specific tier page."""
        lines = []
        
        # Title
        title = f"{workflow.module_name} - {tier}"
        lines.append(title)
        lines.append("=" * len(title))
        lines.append("")
        
        # Metadata
        lines.append(f"**Module:** {workflow.display_name}")
        lines.append("")
        lines.append(f"**Tier:** {tier}")
        lines.append("")
        
        if workflow.docstring:
            lines.append(f"*{workflow.docstring}*")
            lines.append("")
        
        # Use workflow directive to render actual content
        module_path = workflow.module_path.as_posix()
        
        lines.append(f".. workflow:: {module_path}")
        lines.append(f"   :tier: {tier}")
        lines.append("   :show-diagram:")
        lines.append("")
        
        # Navigation links to other tiers
        if len(workflow.declared_tiers) > 1:
            lines.append("----")
            lines.append("")
            lines.append("**Other tiers:**")
            lines.append("")
            
            for other_tier in workflow.declared_tiers:
                if other_tier != tier:
                    page_ref = f"{workflow.display_name.replace('.', '_')}_{other_tier}"
                    lines.append(f"- :doc:`{other_tier} <{page_ref}>`")
            
            lines.append("")
        
        return lines


def get_toc_css() -> str:
    """
    Get CSS styles for the workflow TOC sidebar.
    
    Returns:
        CSS string to include in static files.
    """
    return '''
/* Workflow TOC Sidebar Styles */
.workflow-toc {
    padding: 10px;
    font-size: 0.9em;
}

.workflow-toc-empty {
    color: #888;
    font-style: italic;
    padding: 10px;
}

.workflow-package {
    margin-bottom: 10px;
}

.package-header {
    cursor: pointer;
    padding: 5px 8px;
    background: #f5f5f5;
    border-radius: 4px;
    display: flex;
    align-items: center;
    gap: 5px;
}

.package-header:hover {
    background: #e8e8e8;
}

.toggle-icon {
    font-size: 0.8em;
    width: 15px;
    text-align: center;
}

.package-name {
    font-weight: 600;
}

.module-list {
    list-style: none;
    padding-left: 20px;
    margin: 5px 0;
}

.workflow-module {
    margin: 3px 0;
}

.workflow-module.current > .module-header,
.workflow-module.current > .module-link {
    background: #e3f2fd;
    border-radius: 4px;
}

.module-header {
    cursor: pointer;
    padding: 4px 8px;
    display: flex;
    align-items: center;
    gap: 5px;
}

.module-header:hover {
    background: #f0f0f0;
}

.module-link {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 4px 8px;
    text-decoration: none;
    color: inherit;
}

.module-link:hover {
    background: #f0f0f0;
    text-decoration: none;
}

.tier-list {
    list-style: none;
    padding-left: 25px;
    margin: 3px 0;
}

.tier-item {
    margin: 2px 0;
}

.tier-item a {
    padding: 2px 8px;
    display: block;
    text-decoration: none;
    color: #666;
    font-size: 0.9em;
}

.tier-item a:hover {
    background: #f0f0f0;
    color: #333;
}

.tier-item.current a {
    background: #bbdefb;
    color: #1565c0;
    font-weight: 500;
}
'''


def get_toc_javascript() -> str:
    """
    Get JavaScript for TOC interactivity.
    
    Returns:
        JavaScript string to include in static files.
    """
    return '''
/* Workflow TOC Toggle Functions */

function togglePackage(header) {
    const container = header.parentElement;
    const list = container.querySelector('.module-list');
    const icon = header.querySelector('.toggle-icon');
    
    if (list.style.display === 'none') {
        list.style.display = 'block';
        icon.textContent = '▼';
        container.classList.add('expanded');
    } else {
        list.style.display = 'none';
        icon.textContent = '▶';
        container.classList.remove('expanded');
    }
}

function toggleModule(header) {
    const container = header.parentElement;
    const list = container.querySelector('.tier-list');
    const icon = header.querySelector('.toggle-icon');
    
    if (list.style.display === 'none') {
        list.style.display = 'block';
        icon.textContent = '▼';
    } else {
        list.style.display = 'none';
        icon.textContent = '▶';
    }
}

// Auto-expand current module on page load
document.addEventListener('DOMContentLoaded', function() {
    const currentModule = document.querySelector('.workflow-module.current');
    if (currentModule) {
        // Expand parent package
        const package = currentModule.closest('.workflow-package');
        if (package && !package.classList.contains('expanded')) {
            const header = package.querySelector('.package-header');
            togglePackage(header);
        }
        
        // Expand module tier list if has one
        const tierList = currentModule.querySelector('.tier-list');
        if (tierList && tierList.style.display === 'none') {
            const header = currentModule.querySelector('.module-header');
            if (header) {
                toggleModule(header);
            }
        }
    }
});
'''
