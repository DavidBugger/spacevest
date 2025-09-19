document.addEventListener('DOMContentLoaded', function() {
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
    
    // State
    let banks = [];
    let verificationInProgress = false;
    
    // Event Listeners
    if (addBankAccountBtn) {
        addBankAccountBtn.addEventListener('click', showAddBankAccountModal);
    }
    
    if (closeAddBankAccountBtn) {
        closeAddBankAccountBtn.addEventListener('click', hideAddBankAccountModal);
    }
    
    if (accountNumberInput) {
        // Add debounce to account number input
        let accountNumberTimeout;
        accountNumberInput.addEventListener('input', function() {
            clearTimeout(accountNumberTimeout);
            const accountNumber = this.value.trim();
            
            if (accountNumber.length === 10 && bankSelect.value) {
                accountNumberTimeout = setTimeout(() => {
                    verifyAccountNumber(accountNumber, bankSelect.value);
                }, 500);
            } else {
                hideAccountName();
            }
        });
    }
    
    if (bankSelect) {
        bankSelect.addEventListener('change', function() {
            const accountNumber = accountNumberInput.value.trim();
            if (accountNumber.length === 10 && this.value) {
                verifyAccountNumber(accountNumber, this.value);
            }
        });
    }
    
    if (addBankAccountForm) {
        addBankAccountForm.addEventListener('submit', handleFormSubmit);
    }
    
    // Load banks when modal is shown
    if (addBankAccountModal) {
        addBankAccountModal.addEventListener('shown.bs.modal', loadBanks);
    }
    
    // Functions
    function showAddBankAccountModal() {
        addBankAccountModal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
        loadBanks();
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
        if (banks.length > 0) return;
        
        try {
            const response = await fetch('/api/banking/banks/');
            const data = await response.json();
            
            if (data.status && data.data) {
                banks = data.data;
                updateBankSelect(banks);
            } else {
                throw new Error(data.message || 'Failed to load banks');
            }
        } catch (error) {
            console.error('Error loading banks:', error);
            showVerificationResult('Failed to load banks. Please try again later.');
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
        if (verificationInProgress) return;
        
        verificationInProgress = true;
        showLoading(true);
        hideVerificationResult();
        
        try {
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
            
            if (response.ok && data.status) {
                showAccountName(data.data.account_name);
                showVerificationResult('Account verified successfully!', false);
            } else {
                hideAccountName();
                showVerificationResult(data.message || 'Account verification failed');
            }
        } catch (error) {
            console.error('Error verifying account:', error);
            hideAccountName();
            showVerificationResult('Error verifying account. Please try again.');
        } finally {
            showLoading(false);
            verificationInProgress = false;
        }
    }
    
    async function handleFormSubmit(e) {
        e.preventDefault();
        
        const accountNumber = accountNumberInput.value.trim();
        const bankCode = bankSelect.value;
        
        if (!bankCode) {
            showVerificationResult('Please select a bank');
            return;
        }
        
        if (accountNumber.length !== 10) {
            showVerificationResult('Please enter a valid 10-digit account number');
            return;
        }
        
        // If we already have the account name, submit the form
        if (!accountNameDisplay.classList.contains('hidden')) {
            await saveBankAccount(accountNumber, bankCode);
        } else {
            // Otherwise, verify the account first
            await verifyAccountNumber(accountNumber, bankCode);
        }
    }
    
    async function saveBankAccount(accountNumber, bankCode) {
        showLoading(true);
        
        try {
            const response = await fetch('/api/banking/accounts/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    account_number: accountNumber,
                    bank_code: bankCode,
                    is_primary: true // Make this the primary account
                })
            });
            
            const data = await response.json();
            
            if (response.ok && data.status) {
                showVerificationResult('Bank account added successfully!', false);
                setTimeout(() => {
                    hideAddBankAccountModal();
                    // Refresh the page or update the UI as needed
                    window.location.reload();
                }, 1500);
            } else {
                showVerificationResult(data.message || 'Failed to save bank account');
            }
        } catch (error) {
            console.error('Error saving bank account:', error);
            showVerificationResult('Error saving bank account. Please try again.');
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
