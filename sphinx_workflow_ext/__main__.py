"""
Command-line interface for workflow documentation generator.

Usage:
    python -m generate_workflow_docs <file1> [file2...] [options]
    
Examples:
    # Auto-detects file type by extension
    python -m generate_workflow_docs notebook.ipynb           # Jupyter notebook
    python -m generate_workflow_docs module.py                # Python module (multi-tier)
    python -m generate_workflow_docs nb1.ipynb mod1.py        # Mixed types
    
    # Options
    python -m generate_workflow_docs file.ipynb --output-dir docs/
    python -m generate_workflow_docs file.ipynb --validate-only
    python -m generate_workflow_docs module.py --workflow extraction_overview  # Specific tier only
    python -m generate_workflow_docs module.py --list-workflows               # List available tiers
    python -m generate_workflow_docs file.ipynb --strict --verbose
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional
import logging

from .core import ExtractorConfig, setup_logger, WorkflowDocError
from .validators import NotebookWorkflowValidator, ModuleWorkflowValidator
from .extractors import NotebookWorkflowExtractor
from .extractors.multi_tier_module_extractor import MultiTierModuleExtractor
from .processing import DocumentGenerator
from .parsers.multi_tier_parser import MultiTierParser


class ProcessingStats:
    """Track processing statistics."""
    
    def __init__(self):
        self.total = 0
        self.success = 0
        self.failed = 0
        self.warnings = 0
        self.errors: List[str] = []
    
    def add_success(self, file_name: str):
        """Record successful processing."""
        self.success += 1
        self.total += 1
    
    def add_failure(self, file_name: str, error: str):
        """Record failed processing."""
        self.failed += 1
        self.total += 1
        self.errors.append(f"{file_name}: {error}")
    
    def add_warning(self, message: str):
        """Record a warning."""
        self.warnings += 1
    
    def display_summary(self):
        """Display processing summary."""
        print("\n" + "=" * 60)
        print("PROCESSING SUMMARY")
        print("=" * 60)
        print(f"Total files processed: {self.total}")
        print(f"  [OK] Successful: {self.success}")
        print(f"  [ERR] Failed: {self.failed}")
        print(f"  [WARN] Warnings: {self.warnings}")
        
        if self.errors:
            print("\nERRORS:")
            for error in self.errors:
                print(f"  - {error}")
        
        print("=" * 60)


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate workflow documentation from Jupyter notebooks and Python modules",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        'files',
        nargs='*',
        help='Files to process (.ipynb or .py). Auto-detects type. Required - must specify at least one file.'
    )
    
    parser.add_argument(
        '--output-dir',
        type=Path,
        help='Output directory for generated documentation (default: same directory as source file)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    parser.add_argument(
        '--strict',
        action='store_true',
        help='Strict mode - fail on first error'
    )
    
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only validate workflow markers without generating documentation'
    )
    
    parser.add_argument(
        '--workflow',
        type=str,
        help='[Modules only] Generate documentation for specific workflow tier only'
    )
    
    parser.add_argument(
        '--list-workflows',
        action='store_true',
        help='[Modules only] List available workflow tiers in a Python module'
    )
    
    parser.add_argument(
        '--log-file',
        type=Path,
        help='Write logs to file'
    )
    
    return parser.parse_args()


def detect_file_type(file_path: Path) -> str:
    """
    Detect file type based on extension.
    
    Args:
        file_path: Path to file
    
    Returns:
        'notebook' for .ipynb files, 'module' for .py files
    
    Raises:
        ValueError: If file extension is not supported
    """
    suffix = file_path.suffix.lower()
    
    if suffix == '.ipynb':
        return 'notebook'
    elif suffix == '.py':
        return 'module'
    else:
        raise ValueError(
            f"Unsupported file type: {suffix}. "
            f"Supported types: .ipynb (notebooks), .py (modules)"
        )


def find_source_files(args: argparse.Namespace) -> List[Path]:
    """
    Validate and return source files to process.
    Auto-detects file type by extension (.ipynb or .py).
    
    Args:
        args: Parsed command-line arguments
    
    Returns:
        List of source file paths
    """
    if not args.files:
        print("ERROR: No files specified. Please provide file paths to process.", file=sys.stderr)
        print("Usage: python -m generate_workflow_docs <file1.ipynb> [file2.py] ...", file=sys.stderr)
        sys.exit(1)
    
    # Validate provided files
    files = [Path(f) for f in args.files]
    
    for f in files:
        if not f.exists():
            print(f"ERROR: File not found: {f}", file=sys.stderr)
            sys.exit(1)
        
        # Validate file type
        try:
            detect_file_type(f)
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)
    
    return files


def create_config(args: argparse.Namespace) -> ExtractorConfig:
    """
    Create configuration from arguments.
    
    Args:
        args: Parsed command-line arguments
    
    Returns:
        ExtractorConfig instance
    """
    # Determine log level
    log_level = logging.INFO
    if args.debug:
        log_level = logging.DEBUG
    elif args.verbose:
        log_level = logging.INFO
    
    return ExtractorConfig(
        log_level=log_level,
        verbose=args.verbose,
        debug=args.debug,
        strict_mode=args.strict,
        output_dir=args.output_dir,
        validate_only=getattr(args, 'validate_only', False)
    )


def determine_notebook_output_path(
    notebook_path: Path,
    config: ExtractorConfig
) -> Path:
    """
    Determine output file path for notebook documentation.
    
    Args:
        notebook_path: Path to notebook file
        config: Extractor configuration
    
    Returns:
        Output file path
    """
    # Generate filename
    doc_filename = notebook_path.stem + '.workflow.md'
    
    # Determine directory
    if config.output_dir:
        # User-specified directory
        output_dir = config.output_dir
    else:
        # Same directory as notebook
        output_dir = notebook_path.parent
    
    # Create directory if needed
    output_dir.mkdir(parents=True, exist_ok=True)
    
    return output_dir / doc_filename


def process_notebook_file(
    notebook_path: Path,
    config: ExtractorConfig,
    logger: logging.Logger,
    stats: ProcessingStats
) -> bool:
    """
    Process a single Jupyter notebook file.
    
    Args:
        notebook_path: Path to notebook file (.ipynb)
        config: Extractor configuration
        logger: Logger instance
        stats: Processing statistics
    
    Returns:
        True if successful, False otherwise
    """
    notebook_name = notebook_path.name
    
    try:
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Processing notebook: {notebook_name}")
        logger.info(f"{'=' * 60}")
        
        # Create extractor
        extractor = NotebookWorkflowExtractor(notebook_path, config, logger)
        
        # Load notebook
        load_result = extractor.load()
        if not load_result.success and config.strict_mode:
            raise WorkflowDocError(f"Failed to load notebook: {', '.join(load_result.errors)}")
        
        # Extract metadata
        metadata = extractor.extract_metadata()
        logger.info(f"Extracted metadata: {metadata.analysis_type or 'Unknown'}")
        
        # Extract steps
        steps = extractor.extract_steps()
        logger.info(f"Extracted {len(steps)} workflow steps")
        
        # Validate workflow structure (always run, even if not strict mode)
        validator = NotebookWorkflowValidator(verbose=config.verbose)
        validation = validator.validate_steps(steps)
        
        # Display validation results
        if config.validate_only or config.debug or not validation.is_valid:
            summary = validator.format_summary(validation)
            print(summary)
        
        # In validate-only mode, stop here
        if config.validate_only:
            if not validation.is_valid:
                stats.add_failure(notebook_name, "Validation failed")
                return False
            else:
                stats.add_success(notebook_name)
                return True
        
        # In strict mode, fail on validation errors
        if config.strict_mode and not validation.is_valid:
            raise WorkflowDocError(
                f"Validation failed: {len(validation.errors)} error(s) found"
            )
        
        # Log warnings even in non-strict mode
        for warning in validation.warnings:
            logger.warning(warning)
            stats.add_warning(warning)
        
        # Extract outputs
        outputs = extractor.extract_outputs()
        logger.info(f"Extracted {len(outputs)} output artifacts")
        
        # Extract common issues
        issues = extractor.extract_common_issues()
        
        # Generate documentation
        generator = DocumentGenerator(config, logger)
        markdown = generator.generate(
            notebook_name=notebook_name,
            metadata=metadata,
            steps=steps,
            outputs=outputs,
            issues=issues
        )
        
        # Determine output path
        output_path = determine_notebook_output_path(notebook_path, config)
        
        # Write file
        with open(output_path, 'w', encoding=config.encoding) as f:
            f.write(markdown)
        
        logger.info(f"[OK] Documentation written to: {output_path}")
        stats.add_success(notebook_name)
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Error processing {notebook_name}: {e}")
        
        if config.debug:
            import traceback
            logger.debug(traceback.format_exc())
        
        stats.add_failure(notebook_name, str(e))
        
        if config.strict_mode:
            raise
        
        return False


def process_module_file(
    module_path: Path,
    config: ExtractorConfig,
    logger: logging.Logger,
    stats: ProcessingStats,
    workflow_filter: Optional[str] = None
) -> bool:
    """
    Process a Python module file using multi-tier extraction.
    
    Args:
        module_path: Path to module file (.py)
        config: Extractor configuration
        logger: Logger instance
        stats: Processing statistics
        workflow_filter: Only process specific workflow tier (optional)
    
    Returns:
        True if successful, False otherwise
    """
    module_name = module_path.name
    
    try:
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Processing module: {module_name}")
        logger.info(f"{'=' * 60}")
        
        # Read source for validation
        with open(module_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Validate multi-tier structure
        validator = ModuleWorkflowValidator(verbose=config.verbose)
        validation = validator.validate_module_source(source, module_path)
        
        # Display validation results
        if config.validate_only or config.debug or not validation.is_valid:
            summary = validator.format_summary(validation, module_path.stem)
            print(summary)
        
        # In validate-only mode, stop here
        if config.validate_only:
            if not validation.is_valid:
                stats.add_failure(module_name, "Validation failed")
                return False
            else:
                stats.add_success(module_name)
                return True
        
        # Check if module has multi-tier markers
        if not validation.has_multi_tier:
            logger.warning(
                f"{module_name} has no multi-tier markers. "
                "Module may not generate documentation. "
                "Add WORKFLOW_TIER markers to enable multi-tier documentation."
            )
            # Continue processing - may still extract some content
        
        # In strict mode, fail on validation errors
        if config.strict_mode and not validation.is_valid:
            raise WorkflowDocError(
                f"Multi-tier validation failed: {validation.total_errors} error(s) found"
            )
        
        # Create multi-tier extractor
        extractor = MultiTierModuleExtractor(module_path, config, logger)
        
        # Load module
        load_result = extractor.load()
        if not load_result.success and config.strict_mode:
            raise WorkflowDocError(f"Failed to load module: {', '.join(load_result.errors)}")
        
        # Determine which workflows to generate
        if workflow_filter:
            workflows_to_process = [workflow_filter]
            if workflow_filter not in validation.declared_workflows:
                raise WorkflowDocError(
                    f"Workflow '{workflow_filter}' not found. "
                    f"Available: {', '.join(sorted(validation.declared_workflows))}"
                )
        else:
            workflows_to_process = sorted(validation.declared_workflows)
        
        logger.info(f"Generating documentation for workflow tiers: {', '.join(workflows_to_process)}")
        
        # Determine output directory
        if config.output_dir:
            output_dir = config.output_dir
        else:
            output_dir = module_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Process each workflow tier
        for workflow_name in workflows_to_process:
            logger.info(f"\n  Extracting tier: {workflow_name}")
            
            # Extract workflow for this tier
            workflow_doc = extractor.extract_workflow_for_tier(workflow_name)
            logger.info(f"  Extracted {len(workflow_doc['steps'])} step(s) for {workflow_name}")
            
            # Extract all function steps for hierarchical documentation
            logger.info(f"  Collecting steps from all functions for hierarchical structure")
            all_functions = extractor.extract_all_function_steps(workflow_name)
            logger.info(f"  Collected {len(all_functions)} functions with workflow steps")
            
            # Generate documentation
            generator = DocumentGenerator(config, logger)
            markdown = generator.generate(
                notebook_name=f"{module_path.stem} ({workflow_name})",
                metadata=workflow_doc['metadata'],
                steps=workflow_doc['steps'],
                outputs=[],
                issues=[],
                mlflow_params=None,
                all_functions=all_functions
            )
            
            # Determine output filename
            output_filename = f"{module_path.stem}.{workflow_name}.workflow.md"
            output_path = output_dir / output_filename
            
            # Write file
            with open(output_path, 'w', encoding=config.encoding) as f:
                f.write(markdown)
            
            logger.info(f"  [OK] {workflow_name} tier written to: {output_path}")
        
        logger.info(f"[OK] Multi-tier documentation complete for {module_name}")
        stats.add_success(module_name)
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Error processing multi-tier module {module_name}: {e}")
        
        if config.debug:
            import traceback
            logger.debug(traceback.format_exc())
        
        stats.add_failure(module_name, str(e))
        
        if config.strict_mode:
            raise
        
        return False


def list_module_workflows(module_path: Path, logger: logging.Logger) -> bool:
    """
    List available workflow tiers in a multi-tier module.
    
    Args:
        module_path: Path to module
        logger: Logger instance
    
    Returns:
        True if successful
    """
    try:
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Workflows in: {module_path.name}")
        logger.info(f"{'=' * 60}")
        
        # Read and parse module
        with open(module_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        parser = MultiTierParser(verbose=False)
        result = parser.parse_module_source(source, module_path)
        
        if not result.has_multi_tier_markers:
            print(f"\n✗ No multi-tier workflows found in {module_path.name}")
            print("  (Module uses single-tier DOCUMENT_WORKFLOW)")
            return False
        
        # Display workflows
        print(f"\nDeclared Workflows ({len(result.declared_workflows)}):")
        for workflow in sorted(result.declared_workflows):
            entry_point = parser.get_entry_point_for_workflow(workflow, result)
            print(f"  • {workflow}")
            if entry_point:
                print(f"    Entry point: {entry_point}()")
        
        # Display exclusions
        if result.workflow_exclude_markers:
            print("\nExclusions:")
            for marker in result.workflow_exclude_markers:
                excluded = ', '.join(marker.excluded_workflows)
                print(f"  • {marker.function_name}() excluded from: {excluded}")
        
        print()
        return True
        
    except Exception as e:
        logger.error(f"✗ Error listing workflows: {e}")
        return False


def main():
    """Main entry point."""
    # Parse arguments
    args = parse_arguments()
    
    # Handle --list-workflows for modules
    if args.list_workflows:
        if not args.files:
            print("ERROR: --list-workflows requires a module file path")
            sys.exit(1)
        
        logger = setup_logger(name='workflow_docs', level=logging.INFO)
        module_path = Path(args.files[0])
        
        if not module_path.exists():
            print(f"ERROR: Module not found: {module_path}")
            sys.exit(1)
        
        success = list_module_workflows(module_path, logger)
        sys.exit(0 if success else 1)
    
    # Create configuration
    config = create_config(args)
    
    # Set up logger
    logger = setup_logger(
        name='workflow_docs',
        level=config.log_level,
        log_file=getattr(args, 'log_file', None)
    )
    
    # Find source files
    source_files = find_source_files(args)
    logger.info(f"Found {len(source_files)} file(s) to process")
    
    # Initialize statistics
    stats = ProcessingStats()
    
    # Process each file based on auto-detected type
    for source_path in source_files:
        file_type = detect_file_type(source_path)
        
        if file_type == 'notebook':
            process_notebook_file(source_path, config, logger, stats)
        elif file_type == 'module':
            process_module_file(
                source_path, 
                config, 
                logger, 
                stats,
                workflow_filter=getattr(args, 'workflow', None)
            )
    
    # Display summary
    stats.display_summary()
    
    # Exit with appropriate code
    sys.exit(0 if stats.failed == 0 else 1)


if __name__ == '__main__':
    main()
