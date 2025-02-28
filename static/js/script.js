document.addEventListener('DOMContentLoaded', function() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.getAttribute('data-tab');
            tabBtns.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(tabId).classList.add('active');
        });
    });
    

    const subTabBtns = document.querySelectorAll('.sub-tab-btn');
    const subTabContents = document.querySelectorAll('.sub-tab-content');
    
    subTabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const subtabId = btn.getAttribute('data-subtab');
            const parentTab = btn.closest('.tab-content');
            parentTab.querySelectorAll('.sub-tab-btn').forEach(btn => btn.classList.remove('active'));
            parentTab.querySelectorAll('.sub-tab-content').forEach(content => content.classList.remove('active'));
            btn.classList.add('active');
            parentTab.querySelector(`#${subtabId}`).classList.add('active');
        });
    });

    function showNotification(message, isError = false) {
        const notification = document.getElementById('notification');
        notification.textContent = message;
        notification.classList.remove('hidden');
        notification.classList.add('show');
        
        if (isError) {
            notification.classList.add('error');
        } else {
            notification.classList.remove('error');
        }
        
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                notification.classList.add('hidden');
            }, 300);
        }, 3000);
    }
    
    const copyButtons = document.querySelectorAll('.copy-btn');
    
    copyButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetId = button.getAttribute('data-target');
            const targetElement = document.getElementById(targetId);
            
            targetElement.select();
            document.execCommand('copy');
            
            showNotification('Copied to clipboard!');
        });
    });
    
    document.getElementById('fernet-file-input').addEventListener('change', function() {
        const fileName = this.files[0] ? this.files[0].name : 'No file chosen';
        document.getElementById('fernet-file-name').textContent = fileName;
    });
    
    document.getElementById('generate-fernet-key').addEventListener('click', function() {
        fetch('/generate_fernet_key', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('fernet-key').value = data.key;
                document.getElementById('fernet-key-display').classList.remove('hidden');
                showNotification('Fernet key generated successfully!');
            } else {
                showNotification(data.error || 'Failed to generate key', true);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('An error occurred', true);
        });
    });
    
    document.getElementById('generate-rsa-keys').addEventListener('click', function() {
        fetch('/generate_rsa_keys', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('rsa-public-key').value = data.public_key;
                document.getElementById('rsa-private-key').value = data.private_key;
                document.getElementById('rsa-keys-display').classList.remove('hidden');
                showNotification('RSA key pair generated successfully!');
            } else {
                showNotification(data.error || 'Failed to generate keys', true);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('An error occurred', true);
        });
    });
    
    document.getElementById('encrypt-text-fernet').addEventListener('click', function() {
        const text = document.getElementById('fernet-text-input').value;
        
        if (!text) {
            showNotification('Please enter text to encrypt', true);
            return;
        }
        
        const formData = new FormData();
        formData.append('text', text);
        
        fetch('/encrypt_text_fernet', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('fernet-text-result').value = data.encrypted_text;
                document.getElementById('fernet-text-result-container').classList.remove('hidden');
                showNotification('Text encrypted successfully!');
            } else {
                showNotification(data.error || 'Failed to encrypt text', true);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('An error occurred', true);
        });
    });
    
    document.getElementById('decrypt-text-fernet').addEventListener('click', function() {
        const encryptedText = document.getElementById('fernet-text-input').value;
        
        if (!encryptedText) {
            showNotification('Please enter text to decrypt', true);
            return;
        }
        
        const formData = new FormData();
        formData.append('encrypted_text', encryptedText);
        
        fetch('/decrypt_text_fernet', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('fernet-text-result').value = data.decrypted_text;
                document.getElementById('fernet-text-result-container').classList.remove('hidden');
                showNotification('Text decrypted successfully!');
            } else {
                showNotification(data.error || 'Failed to decrypt text', true);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('An error occurred', true);
        });
    });
    
    document.getElementById('encrypt-text-rsa').addEventListener('click', function() {
        const text = document.getElementById('rsa-text-input').value;
        
        if (!text) {
            showNotification('Please enter text to encrypt', true);
            return;
        }
        
        const formData = new FormData();
        formData.append('text', text);
        
        fetch('/encrypt_text_rsa', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('rsa-text-result').value = data.encrypted_text;
                document.getElementById('rsa-text-result-container').classList.remove('hidden');
                showNotification('Text encrypted successfully!');
            } else {
                showNotification(data.error || 'Failed to encrypt text', true);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('An error occurred', true);
        });
    });
    
    document.getElementById('decrypt-text-rsa').addEventListener('click', function() {
        const encryptedText = document.getElementById('rsa-text-input').value;
        
        if (!encryptedText) {
            showNotification('Please enter text to decrypt', true);
            return;
        }
        
        const formData = new FormData();
        formData.append('encrypted_text', encryptedText);
        
        fetch('/decrypt_text_rsa', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('rsa-text-result').value = data.decrypted_text;
                document.getElementById('rsa-text-result-container').classList.remove('hidden');
                showNotification('Text decrypted successfully!');
            } else {
                showNotification(data.error || 'Failed to decrypt text', true);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('An error occurred', true);
        });
    });
    
    document.getElementById('encrypt-file-fernet').addEventListener('click', function() {
        const fileInput = document.getElementById('fernet-file-input');
        
        if (!fileInput.files || fileInput.files.length === 0) {
            showNotification('Please select a file to encrypt', true);
            return;
        }
        
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        
        fetch('/encrypt_file_fernet', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('fernet-processed-filename').textContent = data.filename;
                document.getElementById('fernet-download-link').href = data.download_url;
                document.getElementById('fernet-file-result-container').classList.remove('hidden');
                showNotification('File encrypted successfully!');
            } else {
                showNotification(data.error || 'Failed to encrypt file', true);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('An error occurred', true);
        });
    });
    
    document.getElementById('decrypt-file-fernet').addEventListener('click', function() {
        const fileInput = document.getElementById('fernet-file-input');
        
        if (!fileInput.files || fileInput.files.length === 0) {
            showNotification('Please select a file to decrypt', true);
            return;
        }
        
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        
        fetch('/decrypt_file_fernet', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('fernet-processed-filename').textContent = data.filename;
                document.getElementById('fernet-download-link').href = data.download_url;
                document.getElementById('fernet-file-result-container').classList.remove('hidden');
                showNotification('File decrypted successfully!');
            } else {
                showNotification(data.error || 'Failed to decrypt file', true);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('An error occurred', true);
        });
    });
});