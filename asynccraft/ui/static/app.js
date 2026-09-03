// Operator selection and workflow state management

(function() {
    'use strict';
    
    const STORAGE_KEY = 'asynccraft_selected_operator';
    const SOP_STATE_KEY = 'asynccraft_sop_state';
    
    // SOP step progression for dispatch workflow
    const DISPATCH_SOP_STEPS = [
        'ingest',
        'create-load',
        'add-equipment',
        'compliance-check',
        'ask-drivers',
        'driver-confirm',
        'traffic-weather',
        'weather-check',
        'delivery-windows',
        'coordinator',
        'delivery',
        'pod-billing'
    ];
    
    // SOP step progression for deal flow workflow
    const DEAL_FLOW_SOP_STEPS = [
        'ingest',
        'score',
        'kyc-gate',
        'partner-notify',
        'crm-writeback',
        'audit'
    ];
    
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
            
            // Reset SOP progression on demo run
            if (e.target.closest('.demo-controls')) {
                resetSOPProgression();
                setTimeout(function() {
                    startSOPProgression();
                }, 500);
            }
        });
    }
    
    // Reinitialize after HTMX swaps
    function setupHTMXListeners() {
        document.body.addEventListener('htmx:afterSwap', function(evt) {
            injectOperatorIntoForms();
            updateWorkflowSteps();
            advanceSOPProgression();
        });
    }
    
    // Update workflow step visualization
    function updateWorkflowSteps() {
        const pendingApprovals = document.querySelectorAll('.approval-card').length;
        const steps = document.querySelectorAll('.workflow-step, .workflow-decision');
        
        if (steps.length === 0) return;
        
        // Find approval gate steps
        steps.forEach(function(step) {
            const stepName = step.dataset.step;
            if (stepName && stepName.includes('approval') || step.classList.contains('approval-gate-step')) {
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
    
    // Reset SOP progression
    function resetSOPProgression() {
        localStorage.removeItem(SOP_STATE_KEY);
        
        // Clear all active/completed states
        document.querySelectorAll('.workflow-step, .workflow-decision').forEach(function(step) {
            step.classList.remove('active', 'completed');
        });
    }
    
    // Start SOP progression animation
    function startSOPProgression() {
        const activeWorkflow = document.querySelector('.workflow-visualization[style*="block"]') || 
                               document.querySelector('.workflow-visualization');
        
        if (!activeWorkflow) return;
        
        const workflowId = activeWorkflow.id;
        const isSOP = workflowId.includes('ops_dispatch');
        const steps = isSOP ? DISPATCH_SOP_STEPS : DEAL_FLOW_SOP_STEPS;
        
        let currentStep = 0;
        
        function progressToNextStep() {
            if (currentStep >= steps.length) return;
            
            const stepName = steps[currentStep];
            const stepElement = activeWorkflow.querySelector(`[data-step="${stepName}"]`);
            
            if (stepElement) {
                // Mark previous step as completed
                if (currentStep > 0) {
                    const prevStepName = steps[currentStep - 1];
                    const prevElement = activeWorkflow.querySelector(`[data-step="${prevStepName}"]`);
                    if (prevElement) {
                        prevElement.classList.remove('active');
                        prevElement.classList.add('completed');
                    }
                }
                
                // Activate current step
                stepElement.classList.add('active');
                stepElement.classList.remove('completed');
                
                // Save state
                const state = {
                    workflow: workflowId,
                    currentStep: currentStep,
                    timestamp: Date.now()
                };
                localStorage.setItem(SOP_STATE_KEY, JSON.stringify(state));
            }
            
            currentStep++;
            
            // Continue progression
            if (currentStep < steps.length) {
                // Check if we need approval (pause at gate steps)
                const stepName = steps[currentStep];
                const isGate = stepName.includes('approval') || stepName.includes('check') || stepName.includes('gate');
                
                if (isGate) {
                    // Pause at gates, wait for actual approval
                    setTimeout(progressToNextStep, 1500);
                } else {
                    // Auto-progress through non-gate steps
                    setTimeout(progressToNextStep, 800);
                }
            }
        }
        
        // Start progression
        progressToNextStep();
    }
    
    // Advance SOP progression (called when approval is made)
    function advanceSOPProgression() {
        const stateStr = localStorage.getItem(SOP_STATE_KEY);
        if (!stateStr) return;
        
        try {
            const state = JSON.parse(stateStr);
            const activeWorkflow = document.getElementById(state.workflow);
            
            if (!activeWorkflow) return;
            
            const isSOP = state.workflow.includes('ops_dispatch');
            const steps = isSOP ? DISPATCH_SOP_STEPS : DEAL_FLOW_SOP_STEPS;
            
            // Continue from current step
            if (state.currentStep < steps.length) {
                const stepName = steps[state.currentStep];
                const stepElement = activeWorkflow.querySelector(`[data-step="${stepName}"]`);
                
                if (stepElement) {
                    stepElement.classList.remove('active');
                    stepElement.classList.add('completed');
                }
                
                // Move to next
                state.currentStep++;
                localStorage.setItem(SOP_STATE_KEY, JSON.stringify(state));
                
                // Continue animation
                setTimeout(function() {
                    if (state.currentStep < steps.length) {
                        const nextStepName = steps[state.currentStep];
                        const nextElement = activeWorkflow.querySelector(`[data-step="${nextStepName}"]`);
                        if (nextElement) {
                            nextElement.classList.add('active');
                        }
                    }
                }, 500);
            }
        } catch (e) {
            console.error('Failed to parse SOP state:', e);
        }
    }
    
    // Restore SOP state on page load
    function restoreSOPState() {
        const stateStr = localStorage.getItem(SOP_STATE_KEY);
        if (!stateStr) return;
        
        try {
            const state = JSON.parse(stateStr);
            
            // Check if state is stale (older than 1 hour)
            if (Date.now() - state.timestamp > 3600000) {
                localStorage.removeItem(SOP_STATE_KEY);
                return;
            }
            
            const activeWorkflow = document.getElementById(state.workflow);
            if (!activeWorkflow) return;
            
            const isSOP = state.workflow.includes('ops_dispatch');
            const steps = isSOP ? DISPATCH_SOP_STEPS : DEAL_FLOW_SOP_STEPS;
            
            // Mark completed steps
            for (let i = 0; i < state.currentStep; i++) {
                const stepName = steps[i];
                const stepElement = activeWorkflow.querySelector(`[data-step="${stepName}"]`);
                if (stepElement) {
                    stepElement.classList.add('completed');
                }
            }
            
            // Mark current active step
            if (state.currentStep < steps.length) {
                const currentStepName = steps[state.currentStep];
                const currentElement = activeWorkflow.querySelector(`[data-step="${currentStepName}"]`);
                if (currentElement) {
                    currentElement.classList.add('active');
                }
            }
        } catch (e) {
            console.error('Failed to restore SOP state:', e);
        }
    }
    
    // Initialize on page load
    document.addEventListener('DOMContentLoaded', function() {
        initOperatorSelector();
        injectOperatorIntoForms();
        setupFormHandlers();
        setupHTMXListeners();
        updateWorkflowSteps();
        restoreSOPState();
    });
})();
