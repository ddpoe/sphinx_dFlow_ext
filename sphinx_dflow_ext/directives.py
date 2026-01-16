"""
Custom Sphinx directives for workflow documentation.

Provides:
- .. workflow:: - Extract workflow from Python module
- .. workflow-notebook:: - Extract workflow from Jupyter notebook
"""

import logging
from dataclasses import asdict
from pathlib import Path
from typing import List, Dict, Any

from docutils import nodes
from docutils.parsers.rst import Directive, directives
from docutils.statemachine import StringList
from sphinx.util import logging as sphinx_logging

from .rst_generator import WorkflowRSTGenerator

logger = sphinx_logging.getLogger(__name__)


class WorkflowDirective(Directive):
    """
    Directive to extract and render workflow from a Python module.
    
    Usage:
        .. workflow:: elastic_net_modules/model_selection.py
           :tier: detailed
           :show-diagram: true
           :collapse-substeps: false
    
    Options:
        tier: Workflow tier (overview, detailed, full) - default: overview
        show-diagram: Show Mermaid flowchart - default: true
        collapse-substeps: Collapse sub-steps by default - default: true
        show-function-calls: Show function call hierarchy - default: true
    """
    
    required_arguments = 1  # Module path
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {
        'tier': directives.unchanged,
        'show-diagram': directives.flag,
        'collapse-substeps': directives.flag,
        'show-function-calls': directives.flag,
    }
    has_content = False
    
    def run(self) -> List[nodes.Node]:
        """Execute the directive."""
        import sys
        
        # Get module path
        module_path_str = self.arguments[0]
        
        # Resolve relative to source directory
        env = self.state.document.settings.env
        
        # Initialize extractor cache if not exists
        if not hasattr(env, 'workflow_extractor_cache'):
            env.workflow_extractor_cache = {}
        source_dir = Path(env.srcdir).parent  # Go up from docs/ to project root
        module_path = source_dir / module_path_str
        
        if not module_path.exists():
            # Try relative to current document
            current_file = Path(self.state.document.current_source)
            module_path = current_file.parent / module_path_str
        
        if not module_path.exists():
            logger.error(f"Module file not found: {module_path_str}")
            error = self.state_machine.reporter.error(
                f'Workflow module not found: {module_path_str}',
                nodes.literal_block('', ''),
                line=self.lineno
            )
            return [error]
        
        # Get options
        tier = self.options.get('tier', 'overview')
        show_diagram = 'show-diagram' in self.options
        collapse_substeps = 'collapse-substeps' not in self.options  # Default True
        show_function_calls = 'show-function-calls' not in self.options  # Default True
        
        # Import extractor from the bundled modules
        try:
            from document_workflow.extractors.multi_tier_module_extractor import MultiTierModuleExtractor
            from document_workflow.core import ExtractorConfig
            from document_workflow.processing.hierarchy_builder import StepHierarchyBuilder
            
        except ImportError as e:
            logger.error(f"Failed to import workflow extractor: {e}")
            error = self.state_machine.reporter.error(
                f'Failed to import workflow extractor: {e}',
                nodes.literal_block('', ''),
                line=self.lineno
            )
            return [error]
        
        # Use cached extractor if available, otherwise create and cache
        cache_key = str(module_path)
        
        if cache_key in env.workflow_extractor_cache:
            extractor = env.workflow_extractor_cache[cache_key]
            logger.debug(f"Using cached extractor for: {module_path.name}")
        else:
            # Create new extractor
            extractor_config = ExtractorConfig(verbose=False, debug=False)
            extractor_logger = logging.getLogger('workflow_extractor')
            extractor_logger.setLevel(logging.WARNING)
            
            extractor = MultiTierModuleExtractor(
                module_path,
                extractor_config,
                extractor_logger
            )
            
            # Load module once
            load_result = extractor.load()
            if not load_result.success:
                raise RuntimeError(f"Failed to load module: {', '.join(load_result.errors)}")
            
            # Cache the loaded extractor
            env.workflow_extractor_cache[cache_key] = extractor
            logger.debug(f"Cached extractor for: {module_path.name}")
        
        try:
            # Extract workflow for requested tier (uses cached parsed data)
            workflow_doc = extractor.extract_workflow_for_tier(tier)
            all_functions = extractor.extract_all_function_steps(tier)
            
            # Build hierarchy from flat steps
            extractor_logger = logging.getLogger('workflow_extractor')
            hierarchy_builder = StepHierarchyBuilder(extractor_logger)
            hierarchical_steps = hierarchy_builder.build_hierarchy(
                root_steps=workflow_doc['steps'],
                all_functions=all_functions
            )
            
            # Get module name from workflow info or use stem
            module_name = workflow_doc.get('module_info', {}).get('module_name', module_path.stem)
            
            # Collect ALL source files referenced by steps (main + external modules)
            all_source_mappings = self._collect_all_source_mappings(hierarchical_steps, module_name, str(module_path))
            
            # Store source mappings in environment for later source generation
            if not hasattr(env, 'workflow_source_mappings'):
                env.workflow_source_mappings = {}
            
            # Merge all source mappings
            for src_module, mapping_data in all_source_mappings.items():
                if src_module in env.workflow_source_mappings:
                    # Merge steps if module already exists
                    existing = env.workflow_source_mappings[src_module]
                    existing['steps'].update(mapping_data['steps'])
                else:
                    env.workflow_source_mappings[src_module] = mapping_data
            
            # DEBUG: Print collected source mappings
            print(f"[SOURCE DEBUG] Collected {len(all_source_mappings)} source modules:")
            for mod_name, data in all_source_mappings.items():
                print(f"  - {mod_name}: {len(data['steps'])} steps, path: {data['source_path']}")
            
            # Convert metadata to dict if it's a dataclass or other object
            metadata = workflow_doc['metadata']
            if hasattr(metadata, '__dataclass_fields__'):
                metadata = asdict(metadata)
            elif isinstance(metadata, (list, tuple)):
                # If metadata is a list, try to convert the first item
                metadata = asdict(metadata[0]) if metadata and hasattr(metadata[0], '__dataclass_fields__') else {}
            elif not isinstance(metadata, dict):
                # If it's some other object, try to convert it
                try:
                    metadata = asdict(metadata)
                except (TypeError, ValueError):
                    metadata = {}
            
            # Generate RST
            config = {
                'show_diagrams': show_diagram,
                'collapse_substeps': collapse_substeps,
                'show_function_calls': show_function_calls,
            }
            
            generator = WorkflowRSTGenerator(config)
            rst_lines = generator.generate_module_rst(
                module_name=module_name,
                metadata=metadata,
                steps=hierarchical_steps,
                all_functions=all_functions
            )
            
            # Parse RST into nodes
            rst_text = '\n'.join(rst_lines)
            node = nodes.container()
            rst_lines_list = StringList(rst_lines, source='workflow-directive')
            self.state.nested_parse(
                rst_lines_list,
                self.content_offset,
                node
            )
            
            return [node]
            
        except Exception as e:
            logger.error(f"Error extracting workflow: {e}")
            error = self.state_machine.reporter.error(
                f'Error extracting workflow from {module_path_str}: {e}',
                nodes.literal_block('', ''),
                line=self.lineno
            )
            return [error]
    
    def _build_step_line_map(self, steps: List[Any]) -> Dict[str, int]:
        """
        Build mapping of step IDs to line numbers for source linking.
        
        Args:
            steps: List of StepInfo objects
        
        Returns:
            Dictionary mapping step IDs to line numbers
        """
        step_line_map = {}
        
        for step in steps:
            step_num = getattr(step, 'hierarchical_number', getattr(step, 'number', ''))
            line_num = getattr(step, 'source_line', None) or getattr(step, 'cell_number', None)
            
            if step_num and line_num:
                step_id = f"step-{str(step_num).replace('.', '-')}"
                step_line_map[step_id] = line_num
            
            sub_steps = getattr(step, 'sub_steps', [])
            if sub_steps:
                sub_map = self._build_step_line_map(sub_steps)
                step_line_map.update(sub_map)
        
        return step_line_map
    
    def _collect_all_source_mappings(
        self, 
        steps: List[Any], 
        default_module: str, 
        default_path: str
    ) -> Dict[str, Dict]:
        """
        Collect source file mappings for ALL modules referenced in steps.
        
        Traverses the hierarchical step tree and groups steps by their source_file,
        creating separate mappings for each module.
        
        Args:
            steps: List of hierarchical step objects
            default_module: Default module name if step doesn't have source_module
            default_path: Default source path if step doesn't have source_file
        
        Returns:
            Dictionary mapping module_name -> {
                'source_path': str,
                'steps': {step_id: {'line': int, 'name': str, 'module': str}, ...}
            }
        """
        from pathlib import Path
        
        source_mappings: Dict[str, Dict] = {}
        
        def _collect_recursive(step: Any):
            # Get source info from step
            source_file = getattr(step, 'source_file', None) or default_path
            source_module = getattr(step, 'source_module', None)
            source_line = getattr(step, 'source_line', None) or getattr(step, 'cell_number', None)
            step_num = getattr(step, 'hierarchical_number', getattr(step, 'number', ''))
            step_name = getattr(step, 'name', '')
            
            # Determine module name from source file if not explicitly set
            if source_module:
                module_name = source_module
            elif source_file:
                # Convert path to module name: /path/to/elastic_net_modules/data_loading.py -> data_loading
                # Or use parent folder if it's a package
                file_path = Path(source_file)
                parent_name = file_path.parent.name
                stem = file_path.stem
                
                # If parent is a package-like name (e.g., elastic_net_modules), include it
                if parent_name and not parent_name.startswith(('.', '_')) and parent_name not in ('src', 'lib'):
                    module_name = f"{parent_name}.{stem}"
                else:
                    module_name = stem
            else:
                module_name = default_module
            
            # Initialize module entry if needed
            if module_name not in source_mappings:
                source_mappings[module_name] = {
                    'source_path': source_file or default_path,
                    'steps': {}
                }
            
            # Add step to mapping if we have line info
            if step_num and source_line:
                step_id = f"step-{str(step_num).replace('.', '-')}"
                source_mappings[module_name]['steps'][step_id] = {
                    'line': source_line,
                    'name': step_name,
                    'number': str(step_num),
                    'module': module_name
                }
            
            # Recurse into children/sub_steps
            children = getattr(step, 'children', []) or getattr(step, 'sub_steps', [])
            for child in children:
                _collect_recursive(child)
        
        # Process all top-level steps
        for step in steps:
            _collect_recursive(step)
        
        # Ensure we always have the default module even if no steps
        if default_module not in source_mappings:
            source_mappings[default_module] = {
                'source_path': default_path,
                'steps': {}
            }
        
        return source_mappings


class WorkflowNotebookDirective(Directive):
    """
    Directive to extract and render workflow from a Jupyter notebook.
    
    Usage:
        .. workflow-notebook:: notebooks/analysis.ipynb
           :show-outputs: true
           :max-output-lines: 50
           :show-issues: true
    
    Options:
        show-outputs: Include output artifacts section - default: true
        max-output-lines: Limit output display - default: 100
        show-issues: Include common issues section - default: true
    """
    
    required_arguments = 1  # Notebook path
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {
        'show-outputs': directives.flag,
        'max-output-lines': directives.positive_int,
        'show-issues': directives.flag,
    }
    has_content = False
    
    def run(self) -> List[nodes.Node]:
        """Execute the directive."""
        # Get notebook path
        notebook_path_str = self.arguments[0]
        
        # Resolve relative to source directory
        env = self.state.document.settings.env
        source_dir = Path(env.srcdir).parent
        notebook_path = source_dir / notebook_path_str
        
        if not notebook_path.exists():
            # Try relative to current document
            current_file = Path(self.state.document.current_source)
            notebook_path = current_file.parent / notebook_path_str
        
        if not notebook_path.exists():
            logger.error(f"Notebook file not found: {notebook_path_str}")
            error = self.state_machine.reporter.error(
                f'Workflow notebook not found: {notebook_path_str}',
                nodes.literal_block('', ''),
                line=self.lineno
            )
            return [error]
        
        # Get options
        show_outputs = 'show-outputs' not in self.options  # Default True
        max_output_lines = self.options.get('max-output-lines', 100)
        show_issues = 'show-issues' not in self.options  # Default True
        
        # Import extractor
        try:
            from document_workflow.extractors import NotebookWorkflowExtractor
            from document_workflow.core import ExtractorConfig
            
        except ImportError as e:
            logger.error(f"Failed to import workflow extractor: {e}")
            error = self.state_machine.reporter.error(
                f'Failed to import workflow extractor: {e}',
                nodes.literal_block('', ''),
                line=self.lineno
            )
            return [error]
        
        # Create extractor
        extractor_config = ExtractorConfig(verbose=False, debug=False)
        extractor_logger = logging.getLogger('workflow_extractor')
        extractor_logger.setLevel(logging.WARNING)
        
        try:
            extractor = NotebookWorkflowExtractor(
                notebook_path,
                extractor_config,
                extractor_logger
            )
            
            # Load notebook
            load_result = extractor.load()
            if not load_result.success:
                raise RuntimeError(f"Failed to load notebook: {', '.join(load_result.errors)}")
            
            # Extract components
            metadata = extractor.extract_metadata()
            steps = extractor.extract_steps()
            outputs = extractor.extract_outputs() if show_outputs else []
            issues = extractor.extract_common_issues() if show_issues else []
            
            # Generate RST
            config = {'max_output_lines': max_output_lines}
            generator = WorkflowRSTGenerator(config)
            
            rst_lines = generator.generate_notebook_rst(
                notebook_name=notebook_path.name,
                metadata=metadata,
                steps=steps,
                outputs=outputs,
                issues=issues
            )
            
            # Parse RST into nodes
            rst_text = '\n'.join(rst_lines)
            node = nodes.container()
            rst_lines_list = StringList(rst_lines, source='workflow-notebook-directive')
            self.state.nested_parse(
                rst_lines_list,
                self.content_offset,
                node
            )
            
            return [node]
            
        except Exception as e:
            logger.error(f"Error extracting notebook workflow: {e}")
            error = self.state_machine.reporter.error(
                f'Error extracting workflow from {notebook_path_str}: {e}',
                nodes.literal_block('', ''),
                line=self.lineno
            )
            return [error]


class WorkflowIndexDirective(Directive):
    """
    Directive to auto-discover and render a workflow index.
    
    Scans specified directories for Python files with workflow markers
    and generates a navigable index of all discovered workflows.
    
    Usage:
        .. workflow-index::
           :search-paths: protocols/, modules/
           :exclude-patterns: test_*, _*
           :title: Workflow Documentation
           :group-by-package: true
    
    Options:
        search-paths: Comma-separated directories to scan (relative to project root)
        exclude-patterns: Comma-separated glob patterns to exclude
        title: Custom title for the index page
        group-by-package: Group modules by package (default: true)
        show-descriptions: Show module docstrings (default: false)
        expand-all: Start with all packages expanded (default: true)
    """
    
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {
        'search-paths': directives.unchanged,
        'exclude-patterns': directives.unchanged,
        'title': directives.unchanged,
        'group-by-package': directives.flag,
        'show-descriptions': directives.flag,
        'expand-all': directives.flag,
    }
    has_content = True  # Allow content for custom intro text
    
    def run(self) -> List[nodes.Node]:
        """Execute the directive."""
        from .discovery import WorkflowDiscovery, DiscoveryResult
        from .toc_generator import WorkflowTOCGenerator
        
        # Get search paths from option or config
        env = self.state.document.settings.env
        
        search_paths_str = self.options.get('search-paths', '')
        if search_paths_str:
            search_paths = [p.strip() for p in search_paths_str.split(',') if p.strip()]
        else:
            # Fall back to config
            search_paths = getattr(env.config, 'workflow_search_paths', [])
        
        if not search_paths:
            logger.warning("No search paths specified for workflow-index directive")
            warning = self.state_machine.reporter.warning(
                'No search paths specified. Use :search-paths: option or set workflow_search_paths in conf.py',
                nodes.literal_block('', ''),
                line=self.lineno
            )
            return [warning]
        
        # Get exclude patterns
        exclude_str = self.options.get('exclude-patterns', '')
        if exclude_str:
            exclude_patterns = [p.strip() for p in exclude_str.split(',') if p.strip()]
        else:
            exclude_patterns = getattr(env.config, 'workflow_exclude_patterns', None)
        
        # Get other options
        title = self.options.get('title', 'Workflow Documentation')
        group_by_package = 'group-by-package' not in self.options  # Default True
        show_descriptions = 'show-descriptions' in self.options
        expand_all = 'expand-all' not in self.options  # Default True
        
        # Resolve base path (project root)
        source_dir = Path(env.srcdir)
        base_path = source_dir.parent  # Go up from docs/ to project root
        
        # Run discovery
        discovery = WorkflowDiscovery(
            base_path=base_path,
            exclude_patterns=exclude_patterns,
            verbose=getattr(env.config, 'workflow_verbose', False)
        )
        
        result = discovery.discover(search_paths)
        
        if not result.workflows:
            # No workflows found
            msg = f"No workflows found in: {', '.join(search_paths)}"
            if result.errors:
                msg += f" (Errors: {', '.join(result.errors)})"
            
            info_node = nodes.paragraph()
            info_node += nodes.emphasis(text=msg)
            return [info_node]
        
        # Store discovery result in environment for later use
        if not hasattr(env, 'workflow_discovery_result'):
            env.workflow_discovery_result = result
        else:
            # Merge with existing
            env.workflow_discovery_result.workflows.update(result.workflows)
        
        # Generate RST content
        toc_config = {
            'group_by_package': group_by_package,
            'show_descriptions': show_descriptions,
            'expand_packages': expand_all,
            'show_tier_counts': True,
        }
        
        generator = WorkflowTOCGenerator(toc_config)
        
        # Build RST lines
        rst_lines = []
        
        # Title
        rst_lines.append(title)
        rst_lines.append("=" * len(title))
        rst_lines.append("")
        
        # Custom content from directive body
        if self.content:
            rst_lines.extend(list(self.content))
            rst_lines.append("")
        
        # Summary box
        total_modules = len(result.workflows)
        all_tiers = result.get_all_tiers()
        packages = result.modules_by_package
        
        rst_lines.append(".. admonition:: Discovery Summary")
        rst_lines.append("")
        rst_lines.append(f"   - **Modules discovered:** {total_modules}")
        rst_lines.append(f"   - **Packages:** {len(packages)}")
        rst_lines.append(f"   - **Available tiers:** {', '.join(sorted(all_tiers)) if all_tiers else 'default'}")
        rst_lines.append("")
        
        # Log any errors/warnings
        if result.errors:
            rst_lines.append(".. warning::")
            rst_lines.append("")
            rst_lines.append("   Discovery encountered errors:")
            rst_lines.append("")
            for error in result.errors[:5]:  # Limit to 5
                rst_lines.append(f"   - {error}")
            rst_lines.append("")
        
        # Generate module listings by package
        modules_by_package = result.modules_by_package
        
        for package_name in sorted(modules_by_package.keys()):
            modules = modules_by_package[package_name]
            display_package = package_name if package_name != "_root" else "Root Modules"
            
            # Package section
            rst_lines.append(display_package)
            rst_lines.append("-" * len(display_package))
            rst_lines.append("")
            
            for workflow in modules:
                # Module entry
                module_header = f"📄 **{workflow.module_name}**"
                if workflow.declared_tiers:
                    module_header += f" ({len(workflow.declared_tiers)} tiers)"
                
                rst_lines.append(module_header)
                rst_lines.append("")
                
                if show_descriptions and workflow.docstring:
                    rst_lines.append(f"   *{workflow.docstring}*")
                    rst_lines.append("")
                
                # Tier links with workflow directives
                if workflow.declared_tiers:
                    rst_lines.append("   **Tiers:**")
                    rst_lines.append("")
                    
                    for tier in workflow.declared_tiers:
                        # Create collapsible section for each tier
                        tier_id = f"{workflow.module_name.replace('.', '-')}-{tier}"
                        rst_lines.append(f"   .. _{tier_id}:")
                        rst_lines.append("")
                        rst_lines.append(f"   **{tier}** tier:")
                        rst_lines.append("")
                        
                        # Get relative path from source dir to module
                        try:
                            rel_path = workflow.module_path.relative_to(base_path)
                        except ValueError:
                            rel_path = workflow.module_path
                        
                        rst_lines.append(f"   .. workflow:: {rel_path.as_posix()}")
                        rst_lines.append(f"      :tier: {tier}")
                        rst_lines.append("")
                
                rst_lines.append("")
        
        # Parse RST into nodes
        node = nodes.container()
        rst_lines_list = StringList(rst_lines, source='workflow-index-directive')
        self.state.nested_parse(
            rst_lines_list,
            self.content_offset,
            node
        )
        
        logger.info(f"Generated workflow index with {total_modules} modules")
        
        return [node]
