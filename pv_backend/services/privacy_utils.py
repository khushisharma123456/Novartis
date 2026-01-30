"""
Privacy Utilities for PV Agent
==============================
Filters PII before sending data to LLM. Ensures no patient-identifying 
information leaves the system.
"""

from typing import Dict, Any, List


class PIIFilter:
    """
    Removes all Personally Identifiable Information from patient data
    before sending to LLM API.
    """
    
    # Fields that contain PII - NEVER send to LLM
    PII_FIELDS = [
        'name', 'email', 'phone', 'address', 'id', 'patient_id',
        'created_by', 'doctors', 'linked_case_id', 'recalled_by'
    ]
    
    # Safe fields that can be sent to LLM
    SAFE_FIELDS = [
        'drug_name', 'symptoms', 'risk_level', 'age', 'gender',
        'case_score', 'completeness_score', 'temporal_clarity_score',
        'medical_confirmation_score', 'followup_responsiveness_score',
        'strength_level', 'strength_score', 'polarity',
        'case_score_interpretation', 'has_clear_timeline',
        'doctor_confirmed', 'hospital_confirmed'
    ]
    
    @classmethod
    def extract_safe_metadata(cls, patient) -> Dict[str, Any]:
        """
        Extract only non-PII data from patient for LLM.
        
        Returns:
            Dict with safe metadata only
        """
        safe_data = {}
        
        for field in cls.SAFE_FIELDS:
            if hasattr(patient, field):
                value = getattr(patient, field)
                if value is not None:
                    safe_data[field] = value
        
        return safe_data
    
    @classmethod
    def get_column_completeness(cls, patient) -> Dict[str, Any]:
        """
        Returns which columns are filled vs missing (no actual values).
        
        Returns:
            Dict with filled_columns and missing_columns lists
        """
        # Important fields to check for completeness
        important_fields = [
            'drug_name', 'symptoms', 'age', 'gender', 'risk_level',
            'symptom_onset_date', 'symptom_resolution_date',
            'doctor_confirmed', 'hospital_confirmed'
        ]
        
        filled = []
        missing = []
        
        for field in important_fields:
            if hasattr(patient, field):
                value = getattr(patient, field)
                if value is not None and value != '' and value != False:
                    filled.append(field)
                else:
                    missing.append(field)
            else:
                missing.append(field)
        
        return {
            'filled_columns': filled,
            'missing_columns': missing,
            'completeness_percent': round(len(filled) / len(important_fields) * 100, 1)
        }
    
    @classmethod
    def validate_no_pii(cls, data: Dict[str, Any]) -> bool:
        """
        Final check before sending to LLM - ensure NO PII.
        
        Returns:
            True if safe, False if PII detected
        """
        for key in data.keys():
            if key.lower() in [f.lower() for f in cls.PII_FIELDS]:
                return False
            
            # Check nested dicts
            if isinstance(data[key], dict):
                if not cls.validate_no_pii(data[key]):
                    return False
        
        return True
    
    @classmethod
    def prepare_for_llm(cls, patient) -> Dict[str, Any]:
        """
        Complete preparation of patient data for LLM.
        Combines safe metadata with column completeness.
        
        Returns:
            Dict ready to send to LLM (validated no PII)
        """
        safe_data = cls.extract_safe_metadata(patient)
        completeness = cls.get_column_completeness(patient)
        
        llm_input = {
            **safe_data,
            **completeness
        }
        
        # Final validation
        if not cls.validate_no_pii(llm_input):
            raise ValueError("PII detected in LLM input - blocking")
        
        return llm_input
