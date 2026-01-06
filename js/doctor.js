/**
 * Doctor Dashboard Logic
 * Manages patient data and dashboard statistics using localStorage.
 */

const STORAGE_PATIENTS = 'medsafe_patients';

export const DoctorApp = {
    // --- Data Management ---

    getPatients: () => {
        return JSON.parse(localStorage.getItem(STORAGE_PATIENTS) || '[]');
    },

    savePatient: (patient) => {
        const patients = DoctorApp.getPatients();
        const existingIndex = patients.findIndex(p => p.id === patient.id);

        if (existingIndex >= 0) {
            patients[existingIndex] = patient;
        } else {
            patients.push(patient);
        }

        localStorage.setItem(STORAGE_PATIENTS, JSON.stringify(patients));
        return patient;
    },

    createPatient: (data) => {
        const newPatient = {
            id: 'PT-' + Math.floor(Math.random() * 10000).toString().padStart(4, '0'),
            created_at: new Date().toISOString(),
            status: 'Monitoring',
            riskLevel: 'Low', // Default
            ...data
        };
        return DoctorApp.savePatient(newPatient);
    },

    // --- Statistics ---

    getStats: () => {
        const patients = DoctorApp.getPatients();
        return {
            total: patients.length,
            highRisk: patients.filter(p => p.riskLevel === 'High').length,
            mediumRisk: patients.filter(p => p.riskLevel === 'Medium').length,
            activeAlerts: patients.filter(p => p.status === 'Alert').length
        };
    },

    // --- Rendering Helpers ---

    renderRiskBadge: (level) => {
        const type = level.toLowerCase();
        return `<span class="badge badge-${type}">${level} Risk</span>`;
    }
};
