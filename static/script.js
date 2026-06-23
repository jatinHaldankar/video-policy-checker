document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('videoFile');
    const fileNameDisplay = document.getElementById('fileNameDisplay');
    const uploadForm = document.getElementById('uploadForm');
    const submitBtn = document.getElementById('submitBtn');
    const uploadStatus = document.getElementById('uploadStatus');
    
    const resultsSection = document.getElementById('resultsSection');
    const jobStatusBadge = document.getElementById('jobStatusBadge');
    const jobIdDisplay = document.getElementById('jobIdDisplay');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const resultsContent = document.getElementById('resultsContent');
    
    const finalStatus = document.getElementById('finalStatus');
    const finalReport = document.getElementById('finalReport');
    const issuesList = document.getElementById('issuesList');
    const checksList = document.getElementById('checksList');

    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    let pollInterval;

    // File input change handler
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            fileNameDisplay.textContent = e.target.files[0].name;
            fileNameDisplay.style.color = 'var(--text-main)';
        } else {
            fileNameDisplay.textContent = 'Choose a video or document...';
            fileNameDisplay.style.color = 'var(--text-muted)';
        }
    });

    // Form submission
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        if (!fileInput.files[0]) return;

        const formData = new FormData(uploadForm);
        
        submitBtn.disabled = true;
        submitBtn.textContent = 'Uploading...';
        uploadStatus.classList.add('hidden');
        resultsSection.classList.add('hidden');
        resultsContent.classList.add('hidden');

        try {
            const response = await fetch('/api/audit', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Upload failed');
            }

            const data = await response.json();
            
            // Show results section in loading state
            resultsSection.classList.remove('hidden');
            loadingIndicator.classList.remove('hidden');
            jobIdDisplay.textContent = data.job_id;
            updateStatusBadge(data.status);
            
            // Start polling
            startPolling(data.job_id);

        } catch (error) {
            showError(error.message);
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Start Audit';
        }
    });

    // Tab switching logic
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.add('hidden'));
            
            btn.classList.add('active');
            document.getElementById(btn.dataset.target).classList.remove('hidden');
            document.getElementById(btn.dataset.target).classList.add('active');
        });
    });

    function startPolling(jobId) {
        if (pollInterval) clearInterval(pollInterval);
        
        pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/status/${jobId}`);
                if (!response.ok) throw new Error('Failed to fetch status');
                
                const data = await response.json();
                updateStatusBadge(data.status);

                if (data.status === 'completed' || data.status === 'failed') {
                    clearInterval(pollInterval);
                    loadingIndicator.classList.add('hidden');
                    resultsContent.classList.remove('hidden');
                    renderResults(data);
                }
            } catch (error) {
                console.error("Polling error:", error);
                clearInterval(pollInterval);
                showError("Lost connection to server while checking status.");
            }
        }, 5000); // Poll every 5 seconds
    }

    function updateStatusBadge(status) {
        jobStatusBadge.textContent = status;
        jobStatusBadge.className = `badge ${status}`;
    }

    function renderResults(data) {
        // Final Status
        const fStatus = data.final_status || 'UNKNOWN';
        finalStatus.textContent = fStatus;
        finalStatus.className = `final-status-badge status-${fStatus}`;
        
        finalReport.textContent = data.final_report || 'No detailed report available.';

        // Compliance Issues
        issuesList.innerHTML = '';
        if (data.compliance_issues && data.compliance_issues.length > 0) {
            data.compliance_issues.forEach(issue => {
                const li = document.createElement('li');
                li.className = 'issue-item';
                
                const sevClass = `sev-${(issue.severity || 'low').toLowerCase()}`;
                
                li.innerHTML = `
                    <div class="issue-header">
                        <strong>${issue.category}</strong>
                        <span class="severity ${sevClass}">${issue.severity}</span>
                    </div>
                    <p>${issue.description}</p>
                    ${issue.timestamp !== 'N/A' ? `<small style="color:var(--text-muted); display:block; margin-top:0.5rem">Time: ${issue.timestamp}</small>` : ''}
                `;
                issuesList.appendChild(li);
            });
        } else {
            issuesList.innerHTML = '<li class="issue-item"><p>No compliance issues found!</p></li>';
        }

        // Pharma Checks
        checksList.innerHTML = '';
        if (data.pharma_checks && data.pharma_checks.length > 0) {
            data.pharma_checks.forEach(check => {
                const li = document.createElement('li');
                li.className = 'check-item';
                
                const passClass = check.passed ? 'check-pass' : 'check-fail';
                const passIcon = check.passed ? '✅' : '❌';
                
                li.innerHTML = `
                    <div class="check-header">
                        <strong>${check.check_name}</strong>
                        <span class="${passClass}">${passIcon} ${check.passed ? 'PASS' : 'FAIL'}</span>
                    </div>
                    <p>${check.details}</p>
                `;
                checksList.appendChild(li);
            });
        } else {
            checksList.innerHTML = '<li class="check-item"><p>No pharma checks data available.</p></li>';
        }
    }

    function showError(message) {
        uploadStatus.textContent = message;
        uploadStatus.className = 'status-message';
        uploadStatus.style.background = 'rgba(239, 68, 68, 0.2)';
        uploadStatus.style.color = '#f87171';
        uploadStatus.style.border = '1px solid rgba(239, 68, 68, 0.5)';
        uploadStatus.classList.remove('hidden');
    }
});
