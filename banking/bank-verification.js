class BankVerification {
  constructor() {
    this.bankSelect = document.getElementById('bank-select');
    this.accountNumberInput = document.getElementById('account-number');
    this.verifyButton = document.getElementById('verify-account');
    this.resultContainer = document.getElementById('verification-result');
    this.spinner = document.getElementById('verification-spinner');
    
    this.init();
  }
  
  async init() {
    await this.loadBanks();
    this.setupEventListeners();
  }
  
  async loadBanks() {
    try {
      this.showLoading(true);
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
      this.showLoading(false);
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
  
  setupEventListeners() {
    this.verifyButton.addEventListener('click', () => this.verifyAccount());
    
    // Auto-verify when account number is entered and bank is selected
    this.accountNumberInput.addEventListener('blur', () => {
      if (this.bankSelect.value && this.accountNumberInput.value) {
        this.verifyAccount();
      }
    });
    
    // Auto-verify when bank is selected and account number is entered
    this.bankSelect.addEventListener('change', () => {
      if (this.accountNumberInput.value && this.bankSelect.value) {
        this.verifyAccount();
      }
    });
  }
  
  async verifyAccount() {
    const bankCode = this.bankSelect.value;
    const accountNumber = this.accountNumberInput.value.trim();
    
    if (!bankCode) {
      this.showError('Please select your bank');
      return;
    }
    
    if (!accountNumber) {
      this.showError('Please enter your account number');
      return;
    }
    
    try {
      this.showLoading(true);
      
      const response = await fetch('/api/banking/verify-account/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCookie('csrftoken')
        },
        body: JSON.stringify({
          account_number: accountNumber,
          bank_code: bankCode
        })
      });
      
      const data = await response.json();
      
      if (response.status === 409) {
        // Account already verified
        this.showSuccess('Account already verified', data.data);
      } else if (response.ok && data.status) {
        // Verification successful
        this.showSuccess('Account verified successfully', data.data);
      } else {
        // Verification failed
        this.showError(data.message || 'Account verification failed');
      }
    } catch (error) {
      console.error('Error verifying account:', error);
      this.showError('An error occurred. Please try again.');
    } finally {
      this.showLoading(false);
    }
  }
  
  showLoading(show) {
    if (show) {
      this.verifyButton.disabled = true;
      this.verifyButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Verifying...';
      if (this.spinner) {
        this.spinner.classList.remove('d-none');
      }
    } else {
      this.verifyButton.disabled = false;
      this.verifyButton.textContent = 'Verify Account';
      if (this.spinner) {
        this.spinner.classList.add('d-none');
      }
    }
  }
  
  showSuccess(message, data) {
    this.resultContainer.innerHTML = `
      <div class="alert alert-success">
        <i class="fas fa-check-circle me-2"></i>
        ${message}
        ${data ? `<div class="mt-2">
          <strong>Account Name:</strong> ${data.account_name}<br>
          <strong>Account Number:</strong> ${data.account_number}<br>
          <strong>Bank:</strong> ${document.querySelector('#bank-select option:checked').textContent}
        </div>` : ''}
      </div>
    `;
  }
  
  showError(message) {
    this.resultContainer.innerHTML = `
      <div class="alert alert-danger">
        <i class="fas fa-exclamation-circle me-2"></i>
        ${message}
      </div>
    `;
  }
  
  getCookie(name) {
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
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('bank-verification-form')) {
    new BankVerification();
  }
});
