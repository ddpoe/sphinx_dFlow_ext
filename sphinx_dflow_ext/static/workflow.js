/**
 * Workflow Documentation Interactive Features
 * 
 * Provides:
 * - Collapsible step sections
 * - Step navigation
 * - Highlight on hover
 * - Smooth scrolling
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // Initialize collapsible sections
    initializeCollapsibleSteps();
    
    // Initialize step navigation
    initializeStepNavigation();
    
    // Initialize step highlighting
    initializeStepHighlighting();
    
    // Initialize copy buttons for code blocks
    initializeCodeCopyButtons();
});


/**
 * Make workflow steps collapsible
 */
function initializeCollapsibleSteps() {
    const steps = document.querySelectorAll('.workflow-step');
    
    steps.forEach(step => {
        const header = step.querySelector('.workflow-step-header');
        const content = step.querySelector('.workflow-step-content');
        
        if (!header || !content) return;
        
        // Add collapse indicator
        const indicator = document.createElement('span');
        indicator.className = 'collapse-indicator';
        indicator.innerHTML = '▼';
        header.insertBefore(indicator, header.firstChild);
        
        // Make header clickable
        header.style.cursor = 'pointer';
        header.addEventListener('click', function() {
            const isCollapsed = content.classList.toggle('collapsed');
            indicator.innerHTML = isCollapsed ? '▶' : '▼';
            
            // Save state
            const stepId = step.dataset.stepId;
            if (stepId) {
                localStorage.setItem(`workflow-step-${stepId}`, isCollapsed ? 'collapsed' : 'expanded');
            }
        });
        
        // Restore state from localStorage
        const stepId = step.dataset.stepId;
        if (stepId) {
            const savedState = localStorage.getItem(`workflow-step-${stepId}`);
            if (savedState === 'collapsed') {
                content.classList.add('collapsed');
                indicator.innerHTML = '▶';
            }
        }
    });
}


/**
 * Create navigation menu for workflow steps
 * Only includes major steps (depth-0) to avoid duplicating the Quick Navigation box
 */
function initializeStepNavigation() {
    // Only select top-level steps (depth-0) to match Quick Navigation box
    const steps = document.querySelectorAll('.workflow-step-depth-0');
    if (steps.length === 0) return;
    
    // Don't create this navigation - we already have Quick Navigation in the RST
    // This was creating a duplicate "Workflow Steps" section with 38 items
    return;
    
    const navList = document.createElement('ul');
    
    steps.forEach((step, index) => {
        const stepNumber = step.dataset.stepNumber || (index + 1);
        const stepTitle = step.dataset.stepTitle || `Step ${stepNumber}`;
        
        const navItem = document.createElement('li');
        const navLink = document.createElement('a');
        navLink.href = `#step-${stepNumber}`;
        navLink.textContent = `${stepNumber}. ${stepTitle}`;
        navLink.addEventListener('click', function(e) {
            e.preventDefault();
            step.scrollIntoView({ behavior: 'smooth', block: 'start' });
            
            // Highlight step briefly
            step.classList.add('highlighted');
            setTimeout(() => step.classList.remove('highlighted'), 2000);
        });
        
        navItem.appendChild(navLink);
        navList.appendChild(navItem);
    });
    
    nav.appendChild(navList);
    
    // Insert navigation before first step
    const firstStep = steps[0];
    firstStep.parentNode.insertBefore(nav, firstStep);
}


/**
 * Highlight steps on hover and when referenced
 */
function initializeStepHighlighting() {
    const steps = document.querySelectorAll('.workflow-step');
    
    steps.forEach(step => {
        step.addEventListener('mouseenter', function() {
            this.classList.add('hover');
        });
        
        step.addEventListener('mouseleave', function() {
            this.classList.remove('hover');
        });
    });
    
    // Handle workflow step references
    const stepRefs = document.querySelectorAll('.workflow-step-ref');
    
    stepRefs.forEach(ref => {
        ref.addEventListener('click', function(e) {
            const stepId = this.dataset.stepId;
            if (!stepId) return;
            
            e.preventDefault();
            
            const targetStep = document.querySelector(`[data-step-id="${stepId}"]`);
            if (targetStep) {
                targetStep.scrollIntoView({ behavior: 'smooth', block: 'start' });
                targetStep.classList.add('highlighted');
                setTimeout(() => targetStep.classList.remove('highlighted'), 2000);
            }
        });
        
        // Add hover effect
        ref.style.cursor = 'pointer';
        ref.addEventListener('mouseenter', function() {
            this.style.textDecoration = 'underline';
        });
        ref.addEventListener('mouseleave', function() {
            this.style.textDecoration = 'none';
        });
    });
}


/**
 * Add copy buttons to code blocks
 */
function initializeCodeCopyButtons() {
    const codeBlocks = document.querySelectorAll('pre');
    
    codeBlocks.forEach(block => {
        const button = document.createElement('button');
        button.className = 'copy-code-button';
        button.textContent = 'Copy';
        button.title = 'Copy code to clipboard';
        
        button.addEventListener('click', function() {
            const code = block.querySelector('code') || block;
            const text = code.textContent;
            
            navigator.clipboard.writeText(text).then(() => {
                button.textContent = 'Copied!';
                button.classList.add('copied');
                
                setTimeout(() => {
                    button.textContent = 'Copy';
                    button.classList.remove('copied');
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy:', err);
                button.textContent = 'Failed';
                setTimeout(() => {
                    button.textContent = 'Copy';
                }, 2000);
            });
        });
        
        block.style.position = 'relative';
        block.appendChild(button);
    });
}


/**
 * Expand/collapse all steps
 */
function expandAllSteps() {
    const steps = document.querySelectorAll('.workflow-step');
    steps.forEach(step => {
        const content = step.querySelector('.workflow-step-content');
        const indicator = step.querySelector('.collapse-indicator');
        if (content && indicator) {
            content.classList.remove('collapsed');
            indicator.innerHTML = '▼';
        }
    });
}

function collapseAllSteps() {
    const steps = document.querySelectorAll('.workflow-step');
    steps.forEach(step => {
        const content = step.querySelector('.workflow-step-content');
        const indicator = step.querySelector('.collapse-indicator');
        if (content && indicator) {
            content.classList.add('collapsed');
            indicator.innerHTML = '▶';
        }
    });
}

// Export functions for external use
window.workflowDocs = {
    expandAll: expandAllSteps,
    collapseAll: collapseAllSteps
};
