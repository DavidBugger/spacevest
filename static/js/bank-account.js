// Global error handler
window.addEventListener('error', function(error) {
    console.error('Global error:', error);
    return false;
});

// Add error handling for the includes issue
if (typeof String.prototype.includes === 'undefined') {
    String.prototype.includes = function(search, start) {
        'use strict';
        if (search instanceof RegExp) {
            throw new TypeError('first argument must not be a RegExp');
        } 
        if (start === undefined) { start = 0; }
        return this.indexOf(search, start) !== -1;
    };
}

console.log('bank-account.js loaded'); // Debug log

document.addEventListener('DOMContentLoaded', function() {
    console.log('=== BANK ACCOUNT SCRIPT LOADED ===');
    
    // Elements
    const addBankAccountBtn = document.getElementById('add-bank-account-btn');
    const addBankAccountModal = document.getElementById('add-bank-account-modal');
    const closeAddBankAccountBtn = document.getElementById('close-add-bank-account');
    const bankSelect = document.getElementById('bank-select');
    const accountNumberInput = document.getElementById('account-number');
    const accountNameDisplay = document.getElementById('account-name-display');
    const accountNameSpan = document.getElementById('account-name');
    const verificationResult = document.getElementById('verification-result');
    const verifyAccountBtn = document.getElementById('verify-account-btn');
    const verificationSpinner = document.getElementById('verification-spinner');
    const addBankAccountForm = document.getElementById('add-bank-account-form');
    const bankDetailsPrompt = document.getElementById('bank-details-prompt');
    
    // Function to setup the change bank button
    function setupChangeBankButton() {
        // Try to find the change bank button using multiple selectors
        const changeBankBtn = document.getElementById('change-bank-btn') || 
                            document.querySelector('button[data-action="change-bank"]');
        
        console.log('Change bank button element:', changeBankBtn); // Debug log
        
        if (changeBankBtn) {
            console.log('Change bank button found, setting up click handler');
            // Remove any existing click event listeners
            const newBtn = changeBankBtn.cloneNode(true);
            changeBankBtn.parentNode.replaceChild(newBtn, changeBankBtn);
            // Add the event listener to the new node
            newBtn.addEventListener('click', handleChangeBank);
            return true;
        }
        return false;
    }
    
    // Try to set up the button immediately
    if (!setupChangeBankButton()) {
        console.log('Change bank button not found, will retry...');
        // If button not found, set up a mutation observer to watch for it
        const observer = new MutationObserver((mutations, obs) => {
            if (setupChangeBankButton()) {
                console.log('Found and set up change bank button via observer');
                obs.disconnect(); // Stop observing once we've found the button
            }
        });
        
        // Start observing the document with the configured parameters
        if (document.body) {
            observer.observe(document.body, { childList: true, subtree: true });
        } else {
            console.error('Document body not found');
        }
    }
    
    // State
    let banks = [];
    let verificationInProgress = false;
    
    // Event Listeners
    if (addBankAccountBtn) {
        addBankAccountBtn.addEventListener('click', showAddBankAccountModal);
    }
    
    // Add event listener for close button
    if (closeAddBankAccountBtn) {
        closeAddBankAccountBtn.addEventListener('click', hideAddBankAccountModal);
    }
    
    // Initialize verify button if it exists
    const verifyButton = document.getElementById('verify-account-btn');
    if (verifyButton) {
        // Make sure it doesn't submit the form
        verifyButton.type = 'button';
        verifyButton.addEventListener('click', function(e) {
            e.preventDefault();
            const accountNumber = accountNumberInput ? accountNumberInput.value.trim() : '';
            const bankCode = bankSelect ? bankSelect.value : '';
            
            if (accountNumber && bankCode) {
                verifyAccountNumber(accountNumber, bankCode);
            } else {
                showVerificationResult('Please enter both bank and account number');
            }
        });
    }
    
    if (changeBankBtn) {
        changeBankBtn.addEventListener('click', handleChangeBank);
    }
    
    if (closeAddBankAccountBtn) {
        closeAddBankAccountBtn.addEventListener('click', hideAddBankAccountModal);
    }
    
    if (accountNumberInput) {
        console.log('Account number input element found');
        // Add debounce to account number input
        let accountNumberTimeout;
        
        // Function to handle verification
        const handleVerification = function() {
            try {
                const accountNumber = this.value.trim();
                console.log('Account number input changed:', accountNumber);
                
                // Get the current bank code
                const bankCode = bankSelect ? bankSelect.value : null;
                console.log('Selected bank code:', bankCode || 'No bank selected');
                
                // If we have exactly 10 digits and a bank is selected
                if (accountNumber.length === 10 && bankCode) {
                    console.log('✅ Conditions met for auto-verification');
                    // Clear any previous timeouts
                    clearTimeout(accountNumberTimeout);
                    // Set a small delay to allow user to finish typing
                    accountNumberTimeout = setTimeout(() => {
                        console.log('🚀 Auto-verifying account:', { accountNumber, bankCode });
                        verifyAccountNumber(accountNumber, bankCode);
                    }, 300);
                } else if (accountNumber.length > 0) {
                    console.log('❌ Conditions not met for auto-verification');
                    console.log('Account length:', accountNumber.length, 'Bank selected:', !!bankCode);
                    hideAccountName();
                } else {
                    console.log('Input cleared or empty');
                    hideAccountName();
                    hideVerificationResult();
                }
            } catch (error) {
                console.error('Error in verification handler:', error);
            }
        }.bind(accountNumberInput);
        
        // Add event listeners
        accountNumberInput.addEventListener('input', handleVerification);
        
        // Handle bank selection changes
        if (bankSelect) {
            bankSelect.addEventListener('change', function() {
                const accountNumber = accountNumberInput ? accountNumberInput.value.trim() : '';
                if (accountNumber.length === 10 && this.value) {
                    console.log('✅ Bank selected with valid account number, triggering verification');
                    verifyAccountNumber(accountNumber, this.value);
                }
            });
        }
    }
    
    if (addBankAccountForm) {
        addBankAccountForm.addEventListener('submit', function(e) {
            e.preventDefault(); // Prevent default form submission
            const accountNumber = accountNumberInput ? accountNumberInput.value.trim() : '';
            const bankCode = bankSelect ? bankSelect.value : '';
            
            if (accountNumber && bankCode) {
                verifyAccountNumber(accountNumber, bankCode);
            } else {
                showVerificationResult('Please fill in all required fields');
            }
        });
    }
    
    // Load banks when modal is shown
    if (addBankAccountModal) {
        addBankAccountModal.addEventListener('shown.bs.modal', loadBanks);
    }
    
    // Functions
    async function handleChangeBank() {
        console.log('Change bank button clicked');
        
        // Check if the modal element exists
        if (!addBankAccountModal) {
            console.error('Bank account modal element not found');
            return;
        }
        
        try {
            const result = await Swal.fire({
                title: 'Change Bank Account',
                html: `
                    <div class="text-left text-gray-800">
                        <div class="flex justify-center mb-4">
                            <div class="w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center">
                                <i class="fas fa-exchange-alt text-yellow-500 text-2xl"></i>
                            </div>
                        </div>
                        <h3 class="text-lg font-semibold text-center mb-3">Are you sure you want to change your bank account?</h3>
                        <div class="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-4 rounded">
                            <div class="flex">
                                <div class="flex-shrink-0">
                                    <svg class="h-5 w-5 text-yellow-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                                        <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                                    </svg>
                                </div>
                                <div class="ml-3">
                                    <p class="text-sm text-yellow-700">
                                        You'll need to verify your new bank account details. 
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                `,
                showCancelButton: true,
                confirmButtonText: 'Continue',
                cancelButtonText: 'Cancel',
                confirmButtonColor: '#2563eb',
                cancelButtonColor: '#6b7280',
                showLoaderOnConfirm: true,
                preConfirm: () => {
                    return new Promise((resolve) => {
                        // Show loading state
                        Swal.showLoading();
                        // Simulate API call or processing
                        setTimeout(() => {
                            resolve();
                        }, 500);
                    });
                },
                customClass: {
                    popup: 'rounded-xl',
                    confirmButton: 'px-6 py-2.5 text-sm font-medium rounded-lg shadow-sm',
                    cancelButton: 'px-6 py-2.5 text-sm font-medium rounded-lg border border-gray-300 shadow-sm',
                    title: 'text-xl font-semibold text-gray-900',
                    htmlContainer: 'text-left',
                    validationMessage: 'mt-2 text-sm text-red-600',
                    actions: 'mt-4 flex justify-end space-x-3',
                },
                buttonsStyling: false,
                reverseButtons: true,
                allowOutsideClick: () => !Swal.isLoading(),
            });

            if (result.isConfirmed) {
                console.log('User confirmed account change');
                // Show the add bank account modal
                showAddBankAccountModal();
            }
        } catch (error) {
            console.error('Error in confirmation dialog:', error);
            // Fallback to default confirm if there's an error with SweetAlert
            if (confirm('Are you sure you want to change your bank account? You will need to verify the new account.')) {
                showAddBankAccountModal();
            }
        }
    }

    async function showAddBankAccountModal() {
        console.log('showAddBankAccountModal called');
        
        if (!addBankAccountModal) {
            console.error('addBankAccountModal element not found');
            return;
        }
        
        console.log('Showing bank account modal');
        addBankAccountModal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
        
        // Load banks if not already loaded
        if (banks.length === 0) {
            console.log('Loading banks...');
            await loadBanks();
        }
    }
    function hideAddBankAccountModal() {
        addBankAccountModal.classList.add('hidden');
        document.body.style.overflow = '';
        resetForm();
    }
    
    function resetForm() {
        if (addBankAccountForm) {
            addBankAccountForm.reset();
        }
        hideAccountName();
        hideVerificationResult();
    }
    
    function hideAccountName() {
        accountNameDisplay.classList.add('hidden');
    }
    
    function showAccountName(name) {
        accountNameSpan.textContent = name;
        accountNameDisplay.classList.remove('hidden');
    }
    
    function showVerificationResult(message, isError = true) {
        verificationResult.textContent = message;
        verificationResult.className = isError ? 'text-red-400 text-sm mt-2' : 'text-green-400 text-sm mt-2';
        verificationResult.classList.remove('hidden');
    }
    
    function hideVerificationResult() {
        verificationResult.classList.add('hidden');
    }
    
    async function loadBanks() {
        console.log('Starting to load banks...');
        if (banks.length > 0) {
            console.log('Banks already loaded, skipping API call');
            return;
        }
        
        try {
            showLoading(true);
            console.log('Fetching banks from API...');
            const response = await fetch('/api/banking/banks/');
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('Banks API response:', data);
            
            // Handle different possible response formats
            let banksData = [];
            
            if (Array.isArray(data)) {
                // Case 1: Response is directly an array of banks
                banksData = data;
            } else if (data && Array.isArray(data.data)) {
                // Case 2: Response has a data property containing the array
                banksData = data.data;
            } else if (data && data.results && Array.isArray(data.results)) {
                // Case 3: Response has a results property (common in DRF pagination)
                banksData = data.results;
            } else {
                console.error('Unexpected API response format:', data);
                throw new Error('Unexpected response format from server');
            }
            
            if (banksData.length === 0) {
                console.warn('Received empty banks list from API');
            } else {
                banks = banksData;
                console.log(`Successfully loaded ${banks.length} banks`);
                updateBankSelect(banks);
            }
            
        } catch (error) {
            console.error('Error loading banks:', error);
            // Show error to user
            await Swal.fire({
                title: 'Error',
                text: 'Failed to load banks. Please try again later.',
                icon: 'error',
                confirmButtonText: 'OK',
                confirmButtonColor: '#2563eb',
                customClass: {
                    popup: 'rounded-xl',
                    confirmButton: 'px-6 py-2.5 text-sm font-medium rounded-lg shadow-sm',
                },
                buttonsStyling: false
            });
            throw error; // Re-throw to be handled by the caller
        } finally {
            showLoading(false);
        }
    }
    
    function updateBankSelect(bankList) {
        if (!bankSelect) return;
        
        bankSelect.innerHTML = '<option value="">Select your bank</option>';
        
        bankList.forEach(bank => {
            const option = document.createElement('option');
            option.value = bank.code;
            option.textContent = bank.name;
            bankSelect.appendChild(option);
        });
    }
    
    async function verifyAccountNumber(accountNumber, bankCode) {
        console.log('verifyAccountNumber called with:', { accountNumber, bankCode });
        
        if (verificationInProgress) {
            console.log('Verification already in progress, skipping...');
            return;
        }
        
        verificationInProgress = true;
        showLoading(true);
        hideVerificationResult();
        
        console.log('Making API call to verify account...');
        
        try {
            console.log('Sending verification request...');
            const response = await fetch('/api/banking/verify-account/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    account_number: accountNumber,
                    bank_code: bankCode
                })
            });
            
            const data = await response.json();
            console.log('Verification response:', { status: response.status, data });
            
            if (response.ok && data.status) {
                console.log('Verification successful, account name:', data.data.account_name);
                showAccountName(data.data.account_name);
                showVerificationResult('Account verified successfully!', false);
                
                // Reload the page after 2 seconds to reflect changes
                setTimeout(() => {
                    window.location.reload();
                }, 2000);
            } else {
                console.log('Verification failed:', data.message || 'No error message');
                hideAccountName();
                showVerificationResult(data.message || 'Account verification failed');
            }
        } catch (error) {
            console.error('Error verifying account:', error);
            console.error('Error details:', {
                name: error.name,
                message: error.message,
                stack: error.stack
            });
            hideAccountName();
            showVerificationResult('Error verifying account. Please try again.');
        } finally {
            showLoading(false);
            verificationInProgress = false;
        }
    }
    
    async function handleFormSubmit() {
        const accountNumber = accountNumberInput ? accountNumberInput.value.trim() : '';
        const bankCode = bankSelect ? bankSelect.value : '';
        
        if (!accountNumber || !bankCode) {
            showVerificationResult('Please fill in all required fields');
            return;
        }
        
        // If account is already verified, save it
        if (accountNameDisplay && accountNameDisplay.style.display !== 'none') {
            await saveBankAccount(accountNumber, bankCode);
        } else {
            // Otherwise, verify the account first
            await verifyAccountNumber(accountNumber, bankCode);
        }
    }
    
    async function saveBankAccount(accountNumber, bankCode) {
        try {
            showLoading(true);
            const response = await fetch('/api/bank-accounts/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    account_number: accountNumber,
                    bank_code: bankCode
                })
            });

            const data = await response.json();

            if (response.ok) {
                // Show success message
                showVerificationResult('Bank account added successfully!', false);
                // Reset form and close modal after delay
                setTimeout(() => {
                    resetForm();
                    hideAddBankAccountModal();
                    // Reload the page to show the updated bank account
                    window.location.reload();
                }, 1500);
            } else {
                throw new Error(data.detail || 'Failed to save bank account');
            }
        } catch (error) {
            console.error('Error saving bank account:', error);
            showVerificationResult(error.message || 'An error occurred while saving your bank account');
        } finally {
            showLoading(false);
        }
    }
    
    function showLoading(isLoading) {
        if (isLoading) {
            verificationSpinner.classList.remove('hidden');
            verifyAccountBtn.disabled = true;
        } else {
            verificationSpinner.classList.add('hidden');
            verifyAccountBtn.disabled = false;
        }
    }
    
    // Helper function to get CSRF token
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});
