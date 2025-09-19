class BankVerification {
    constructor() {
        this.bankSelect = document.getElementById('bank-select');
        this.accountNumberInput = document.getElementById('account-number');
        this.verifyButton = document.getElementById('verify-account');
        this.verificationResult = document.getElementById('verification-result');
        this.loadingSpinner = document.getElementById('verification-spinner');
        this.bankAccountsList = document.getElementById('bank-accounts-list');
        this.bankAccountTemplate = document.getElementById('bank-account-template');
        this.primaryBadgeTemplate = document.getElementById('primary-badge-template');
        this.makePrimaryTemplate = document.getElementById('make-primary-template');
        
        // CSRF token for Django
        this.csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        
        this.init();
    }
    
    async init() {
        try {
            // Load banks when the page loads
            await this.loadBanks();
            
            // Load user's existing bank accounts
            await this.loadUserBankAccounts();
            
            // Add event listeners
            if (this.verifyButton) {
                this.verifyButton.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.verifyAccount();
                });
            }
            
            // Event delegation for bank accounts list
            if (this.bankAccountsList) {
                this.bankAccountsList.addEventListener('click', (e) => {
                    const button = e.target.closest('button');
                    if (!button) return;
                    
                    const action = button.dataset.action;
                    const accountId = button.dataset.id;
                    
                    if (action === 'make-primary') {
                        this.setPrimaryAccount(accountId);
                    } else if (action === 'remove') {
                        this.deleteAccount(accountId);
                    }
                });
            }
            
            // Auto-submit form when bank and account number are filled
            if (this.bankSelect && this.accountNumberInput) {
                this.accountNumberInput.addEventListener('blur', () => {
                    if (this.bankSelect.value && this.accountNumberInput.value) {
                        this.verifyAccount();
                    }
                });
            }
        } catch (error) {
            console.error('Error initializing bank verification:', error);
            this.showError('Failed to initialize bank verification. Please refresh the page.');
        }
    }
    
    async loadBanks() {
        try {
            this.setLoading(true);
            const response = await fetch('/api/banking/banks/');
            const data = await response.json();
            
            if (data.status && data.data) {
                this.populateBanks(data.data);
            } else {
                this.showError('Failed to load banks. Please try again.');
            }
        } catch (error) {
            console.error('Error loading banks:', error);
            this.showError('Error loading banks. Please refresh the page.');
        } finally {
            this.setLoading(false);
        }
    }
    
    populateBanks(banks) {
        // Clear existing options
        this.bankSelect.innerHTML = '<option value="">Select your bank</option>';
        
        // Add banks to select
        banks.forEach(bank => {
            const option = document.createElement('option');
            option.value = bank.code;
            option.textContent = bank.name;
            this.bankSelect.appendChild(option);
        });
    }
    
    async loadUserBankAccounts() {
        try {
            const response = await fetch('/api/banking/user-accounts/');
            const data = await response.json();
            
            if (data.status && data.data) {
                this.renderBankAccounts(data.data);
            } else {
                this.showError('Failed to load bank accounts. Please try again.');
            }
        } catch (error) {
            console.error('Error loading bank accounts:', error);
            this.showError('Error loading bank accounts. Please refresh the page.');
        }
    }
    
    renderBankAccounts(accounts) {
        if (!this.bankAccountsList) return;
        
        this.bankAccountsList.innerHTML = '';
        
        if (!accounts || accounts.length === 0) {
            this.bankAccountsList.innerHTML = `
                <div class="text-center py-4 text-gray-400">
                    <i class="fas fa-university text-2xl mb-2"></i>
                    <p>No bank accounts added yet</p>
                </div>
            `;
            return;
        }
        
        // Sort accounts with primary account first
        const sortedAccounts = [...accounts].sort((a, b) => 
            (b.is_primary ? 1 : 0) - (a.is_primary ? 1 : 0)
        );
        
        sortedAccounts.forEach(account => {
            const accountElement = this.createBankAccountElement(account);
            if (accountElement) {
                this.bankAccountsList.appendChild(accountElement);
            }
        });
    }
    
    createBankAccountElement(account) {
        const accountElement = this.bankAccountTemplate.content.cloneNode(true);
        
        accountElement.querySelector('.account-name').textContent = account.account_name;
        accountElement.querySelector('.account-number').textContent = account.account_number;
        accountElement.querySelector('.bank-name').textContent = account.bank_name;
        
        if (account.is_primary) {
            const primaryBadge = this.primaryBadgeTemplate.content.cloneNode(true);
            accountElement.querySelector('.account-info').appendChild(primaryBadge);
        }
        
        const makePrimaryButton = this.makePrimaryTemplate.content.cloneNode(true);
        makePrimaryButton.querySelector('button').dataset.id = account.id;
        accountElement.querySelector('.account-actions').appendChild(makePrimaryButton);
        
        const removeButton = document.createElement('button');
        removeButton.textContent = 'Remove';
        removeButton.dataset.action = 'remove';
        removeButton.dataset.id = account.id;
        accountElement.querySelector('.account-actions').appendChild(removeButton);
        
        return accountElement;
    }
    
    async verifyAccount() {
        const bankCode = this.bankSelect.value;
        const accountNumber = this.accountNumberInput.value.trim();
        
        if (!bankCode) {
            this.showError('Please select a bank');
            this.bankSelect.focus();
            return;
        }
        
        if (!accountNumber) {
            this.showError('Please enter account number');
            this.accountNumberInput.focus();
            return;
        }
        
        // Basic account number validation (10 digits for most Nigerian banks)
        if (!/^\d{10,11}$/.test(accountNumber)) {
            this.showError('Please enter a valid 10 or 11 digit account number');
            this.accountNumberInput.focus();
            return;
        }
        
        this.setLoading(true);
        
        try {
            const response = await fetch('/api/banking/verify-account/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    bank_code: bankCode,
                    account_number: accountNumber
                })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.detail || data.message || 'Verification failed');
            }
            
            this.showSuccess(`Account verified: ${data.account_name}`);
            
            // Clear the form
            this.accountNumberInput.value = '';
            
            // Reload the bank accounts list
            await this.loadUserBankAccounts();
            
        } catch (error) {
            console.error('Verification error:', error);
            this.showError(error.message || 'Failed to verify account. Please check the details and try again.');
        } finally {
            this.setLoading(false);
        }
    }
    
    async setPrimaryAccount(accountId) {
        try {
            const response = await fetch(`/api/banking/accounts/${accountId}/make-primary/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                }
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.detail || data.message || 'Failed to set primary account');
            }
            
            this.showSuccess('Primary account updated successfully');
            
            // Reload the bank accounts list
            await this.loadUserBankAccounts();
        } catch (error) {
            console.error('Error setting primary account:', error);
            this.showError(error.message || 'Failed to set primary account. Please try again.');
        }
    }
    
    async deleteAccount(accountId) {
        try {
            const response = await fetch(`/api/banking/accounts/${accountId}/`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                }
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.detail || data.message || 'Failed to delete account');
            }
            
            this.showSuccess('Account deleted successfully');
            
            // Reload the bank accounts list
            await this.loadUserBankAccounts();
        } catch (error) {
            console.error('Error deleting account:', error);
            this.showError(error.message || 'Failed to delete account. Please try again.');
        }
    }
    
    setLoading(show) {
        if (show) {
            this.verifyButton.disabled = true;
            this.verifyButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Verifying...';
            if (this.loadingSpinner) {
                this.loadingSpinner.classList.remove('d-none');
            }
        } else {
            this.verifyButton.disabled = false;
            this.verifyButton.textContent = 'Verify Account';
            if (this.loadingSpinner) {
                this.loadingSpinner.classList.add('d-none');
            }
        }
    }
    
    showSuccess(message) {
        if (!this.verificationResult) {
            console.log('Success:', message);
            return;
        }
        
        this.verificationResult.innerHTML = `
            <div class="bg-green-500/10 border border-green-500/30 text-green-300 p-3 rounded-lg mb-4 flex items-start">
                <i class="fas fa-check-circle mt-0.5 mr-2"></i>
                <span>${this.escapeHtml(message)}</span>
            </div>
        `;
        
        // Auto-hide success after 5 seconds
        setTimeout(() => {
            if (this.verificationResult) {
                this.verificationResult.innerHTML = '';
            }
        }, 5000);
    }
    
    showError(message) {
        if (!this.verificationResult) {
            console.error('Error:', message);
            return;
        }
        
        this.verificationResult.innerHTML = `
            <div class="bg-red-500/10 border border-red-500/30 text-red-300 p-3 rounded-lg mb-4 flex items-start">
                <i class="fas fa-exclamation-circle mt-0.5 mr-2"></i>
                <span>${this.escapeHtml(message)}</span>
            </div>
        `;
        
        // Auto-hide error after 5 seconds
        setTimeout(() => {
            if (this.verificationResult) {
                this.verificationResult.innerHTML = '';
            }
        }, 5000);
    }
    
    escapeHtml(unsafe) {
        if (typeof unsafe !== 'string') return unsafe;
        return unsafe
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
}

// Initialize when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => {
    // Only initialize on the bank verification page
    if (document.getElementById('bank-verification-form')) {
        new BankVerification();
    }
});
