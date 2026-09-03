// Operator selection and workflow state management

(function() {
    'use strict';
    
    const STORAGE_KEY = 'asyncraft_selected_operator';
    
    // Initialize operator selection from localStorage
    function initOperatorSelector() {
        const selector = document.getElementById('operator-selector');
        if (!selector) return;
        
        const savedOperator = localStorage.getItem(STORAGE_KEY);
        if (savedOperator) {
            selector.value = savedOperator;
            updateOperatorDisplay(savedOperator);
        }
        
        selector.addEventListener('change', function() {
            const selected = this.value;
            localStorage.setItem(STORAGE_KEY, selected);
            updateOperatorDisplay(selected);
        });
    }
    
    // Update the display of selected operator
    function updateOperatorDisplay(operatorName) {
        const display = document.getElementById('selected-operator-display');
        if (display) {
            display.textContent = operatorName || 'None selected';
        }
    }
    
    // Inject selected operator into approval forms
    function injectOperatorIntoForms() {
        const selector = document.getElementById('operator-selector');
        if (!selector || !selector.value) return;
        
        const operatorName = selector.value;
        
        // Find all approval forms and inject hidden input
        document.querySelectorAll('.approval-actions form').forEach(function(form) {
            let hiddenInput = form.querySelector('input[name="approver_name"]');
            if (!hiddenInput) {
                hiddenInput = document.createElement('input');
                hiddenInput.type = 'hidden';
                hiddenInput.name = 'approver_name';
                form.appendChild(hiddenInput);
            }
            hiddenInput.value = operatorName;
        });
    }
    
    // Handle form submissions
    function setupFormHandlers() {
        document.addEventListener('submit', function(e) {
            if (e.target.closest('.approval-actions')) {
                const selector = document.getElementById('operator-selector');
                if (!selector || !selector.value) {
                    e.preventDefault();
                    alert('Please select an operator before approving or rejecting.');
                    return false;
                }
                injectOperatorIntoForms();
            }
        });
    }
    
    // Reinitialize after HTMX swaps
    function setupHTMXListeners() {
        document.body.addEventListener('htmx:afterSwap', function(evt) {
            injectOperatorIntoForms();
            updateWorkflowSteps();
        });
    }
    
    // Update workflow step visualization
    function updateWorkflowSteps() {
        const pendingApprovals = document.querySelectorAll('.approval-card').length;
        const steps = document.querySelectorAll('.workflow-step');
        
        if (steps.length === 0) return;
        
        // Find the approval gate step
        steps.forEach(function(step) {
            if (step.dataset.step === 'approval-gate') {
                if (pendingApprovals > 0) {
                    step.classList.add('active');
                    step.classList.remove('completed');
                } else {
                    step.classList.remove('active');
                    step.classList.add('completed');
                }
            }
        });
    }
    
    // Initialize on page load
    document.addEventListener('DOMContentLoaded', function() {
        initOperatorSelector();
        injectOperatorIntoForms();
        setupFormHandlers();
        setupHTMXListeners();
        updateWorkflowSteps();
    });
})();
