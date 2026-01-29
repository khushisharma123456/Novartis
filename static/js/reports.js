// Report Submission History JavaScript
lucide.createIcons();

let submissionHistory = [];

// Fetch submission history from database
async function loadSubmissionHistory() {
    try {
        console.log('Fetching submission history from /api/side-effect-reports...');
        const response = await fetch('/api/side-effect-reports');
        const data = await response.json();
        console.log('API Response:', data);
        
        if (data.success) {
            submissionHistory = data.reports || [];
            console.log(`Loaded ${submissionHistory.length} reports from database`);
            renderSubmissionHistory();
        }
    } catch (error) {
        console.error('Error loading submission history:', error);
    }
}

function renderSubmissionHistory() {
    const tbody = document.getElementById('historyBody');
    
    if (submissionHistory.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 2rem; color: var(--text-muted);">No submissions yet</td></tr>';
        return;
    }
    
    tbody.innerHTML = submissionHistory.map(report => `
        <tr>
            <td><span class="type-badge type-${report.reportType === 'patient-linked' ? 'linked' : 'anonymised'}">${report.reportType === 'patient-linked' ? 'Patient-linked' : 'Anonymised'}</span></td>
            <td>${report.drugName}</td>
            <td>${new Date(report.dateSubmitted).toLocaleDateString()}</td>
            <td><span class="status-badge status-submitted">${report.status}</span></td>
        </tr>
    `).join('');
}

// Submit new report
async function submitReportToDatabase(reportType, patientId = null) {
    const drugName = document.querySelector('input[placeholder="e.g., Aspirin, Metformin"]').value;
    const sideEffect = document.querySelector('textarea[placeholder="Describe what you observed..."]').value;
    const severity = document.getElementById('severitySelect')?.value || 'Medium';
    const dosage = document.querySelector('input[placeholder="e.g., 500mg"]')?.value || '';
    const onsetDate = document.querySelector('input[type="date"]')?.value || null;
    const outcome = document.querySelector('select[required]:last-of-type')?.value || 'unknown';
    
    // Get patient details for patient-linked reports
    let patientName = null;
    let patientAge = null;
    let patientGender = null;
    let patientPhone = null;
    let patientEmail = null;
    
    if (reportType === 'patient-linked') {
        const manualMode = document.getElementById('manualPatientMode');
        const existingMode = document.getElementById('existingPatientMode');
        
        // Check if manual mode is active (NOT hidden)
        if (manualMode && !manualMode.classList.contains('hidden-section')) {
            // Manual entry mode - get from form fields
            patientName = document.getElementById('manualPatientName')?.value || null;
            patientAge = document.getElementById('manualPatientAge')?.value || null;
            patientGender = document.getElementById('manualPatientGender')?.value || null;
            patientPhone = document.getElementById('manualPatientPhone')?.value || null;
            patientEmail = document.getElementById('manualPatientEmail')?.value || null;
        }
    }
    
    console.log('Submitting report:', { drugName, sideEffect, severity, reportType, patientId, patientName, patientAge, patientGender, patientPhone, patientEmail });
    
    try {
        const response = await fetch('/api/report-side-effect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                drug_name: drugName,
                side_effect: sideEffect,
                severity: severity,
                patient_id: patientId,
                report_type: reportType,
                dosage: dosage,
                onset_date: onsetDate,
                outcome: outcome,
                // Patient details for new patient creation
                patient_name: patientName,
                patient_age: patientAge,
                patient_gender: patientGender,
                patient_phone: patientPhone,
                patient_email: patientEmail
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            console.log('Report submitted successfully:', data);
            
            // Show case matching info if available
            if (data.case_matching) {
                console.log('Case matching result:', data.case_matching);
                if (data.case_matching.action === 'LINKED') {
                    console.log(`Case linked to existing patient: ${data.case_matching.linked_to}`);
                } else if (data.case_matching.action === 'NEW') {
                    console.log(`New patient record created: ${data.patient_id}`);
                }
            }
            
            // Reload submission history
            await loadSubmissionHistory();
            return true;
        } else {
            console.error('Failed to submit report:', data.message);
            alert('Error: ' + (data.message || 'Failed to submit report'));
            return false;
        }
    } catch (error) {
        console.error('Error submitting report:', error);
        alert('Error submitting report: ' + error.message);
        return false;
    }
}

// Load history when page loads
window.addEventListener('DOMContentLoaded', function() {
    loadSubmissionHistory();
});

// Export functions for use in inline scripts
window.loadSubmissionHistory = loadSubmissionHistory;
window.submitReportToDatabase = submitReportToDatabase;
