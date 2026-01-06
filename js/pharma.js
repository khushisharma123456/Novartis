/**
 * Pharma Intelligence Logic
 * Aggregates data from localStorage for population-level analysis.
 */

const STORAGE_PATIENTS = 'medsafe_patients';

export const PharmaApp = {
    getAllData: () => {
        return JSON.parse(localStorage.getItem(STORAGE_PATIENTS) || '[]');
    },

    getAggregateStats: () => {
        const data = PharmaApp.getAllData();
        return {
            totalReports: data.length,
            highRiskCount: data.filter(p => p.riskLevel === 'High').length,
            avgAge: data.length > 0 ? Math.round(data.reduce((acc, p) => acc + parseInt(p.age), 0) / data.length) : 0,
            genderDist: {
                male: data.filter(p => p.gender === 'Male').length,
                female: data.filter(p => p.gender === 'Female').length,
                other: data.filter(p => p.gender === 'Other').length
            }
        };
    },

    getRiskDistribution: () => {
        const data = PharmaApp.getAllData();
        return {
            low: data.filter(p => p.riskLevel === 'Low').length,
            medium: data.filter(p => p.riskLevel === 'Medium').length,
            high: data.filter(p => p.riskLevel === 'High').length,
        };
    }
};
