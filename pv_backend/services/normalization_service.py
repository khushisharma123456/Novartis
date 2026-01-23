"""
Normalization Service for the Pharmacovigilance system.
Converts raw experience events into normalized, structured data.
"""
import hashlib
from datetime import datetime
from typing import Optional, Dict, List, Tuple

from pv_backend.models import (
    db, ExperienceEvent, NormalizedExperience, Polarity,
    AuditLog, AuditAction
)


# Keywords that suggest adverse event
AE_KEYWORDS = [
    'adverse', 'reaction', 'side effect', 'allergy', 'allergic',
    'nausea', 'vomiting', 'headache', 'dizziness', 'rash',
    'pain', 'swelling', 'fever', 'fatigue', 'weakness',
    'bleeding', 'bruising', 'infection', 'inflammation',
    'hospitalized', 'hospitalization', 'emergency', 'serious',
    'severe', 'death', 'died', 'fatal', 'life-threatening',
    'disability', 'discontinued', 'stopped due to'
]

# Keywords that suggest no adverse event
NO_AE_KEYWORDS = [
    'well tolerated', 'no side effects', 'no adverse', 'no reaction',
    'effective', 'working well', 'improved', 'better', 'recovered',
    'no complaints', 'no issues', 'no problems', 'satisfactory',
    'as expected', 'normal', 'good response', 'positive outcome'
]

# Mandatory fields for complete PV data
MANDATORY_FIELDS = [
    'drug_name', 'patient_identifier_hash', 'observed_events'
]


class NormalizationService:
    """
    Service for normalizing experience events.
    
    PV Context:
    - Normalization is essential for consistent analysis
    - Polarity and strength determine the case score
    - Missing fields trigger follow-up requests
    """
    
    ALGORITHM_VERSION = '1.0.0'
    
    @staticmethod
    def normalize_drug_name(drug_name: str) -> str:
        """
        Normalize drug name to a standard format.
        
        PV Context:
        - Drug names can be brand or generic
        - Normalization enables accurate case linking
        """
        if not drug_name:
            return ''
        
        # Basic normalization: lowercase, strip whitespace
        normalized = drug_name.lower().strip()
        
        # Remove common suffixes
        for suffix in [' tablet', ' capsule', ' injection', ' syrup', ' cream', ' ointment']:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
        
        return normalized
    
    @staticmethod
    def normalize_patient_identifier(identifier: str) -> str:
        """
        Normalize patient identifier (already hashed on input).
        
        PV Context:
        - Patient identifiers are ALWAYS hashed for privacy
        - Normalization ensures consistent linking
        """
        if not identifier:
            return ''
        return identifier.lower().strip()
    
    @staticmethod
    def determine_polarity(observed_events: str, outcome: str = None) -> Tuple[Polarity, float, str]:
        """
        Determine polarity (AE/NO_AE/UNCLEAR) from text.
        
        PV Context:
        - Polarity is the SIGN of the score (positive or negative)
        - AE = negative experience (score will be negative)
        - NO_AE = positive experience (score will be positive)
        - UNCLEAR = insufficient data (score will be 0)
        
        Returns:
            Tuple of (polarity, confidence, reasoning)
        """
        if not observed_events:
            return Polarity.UNCLEAR, 0.0, 'No observed events provided'
        
        text = (observed_events + ' ' + (outcome or '')).lower()
        
        # Count keyword matches
        ae_matches = sum(1 for kw in AE_KEYWORDS if kw in text)
        no_ae_matches = sum(1 for kw in NO_AE_KEYWORDS if kw in text)
        
        # Determine polarity based on keyword matches
        if ae_matches > 0 and no_ae_matches == 0:
            confidence = min(1.0, ae_matches * 0.2)
            return Polarity.AE, confidence, f'AE keywords detected: {ae_matches} matches'
        
        elif no_ae_matches > 0 and ae_matches == 0:
            confidence = min(1.0, no_ae_matches * 0.2)
            return Polarity.NO_AE, confidence, f'No-AE keywords detected: {no_ae_matches} matches'
        
        elif ae_matches > no_ae_matches:
            confidence = min(1.0, (ae_matches - no_ae_matches) * 0.15)
            return Polarity.AE, confidence, f'Mixed signals, AE dominant: AE={ae_matches}, NO_AE={no_ae_matches}'
        
        elif no_ae_matches > ae_matches:
            confidence = min(1.0, (no_ae_matches - ae_matches) * 0.15)
            return Polarity.NO_AE, confidence, f'Mixed signals, NO_AE dominant: AE={ae_matches}, NO_AE={no_ae_matches}'
        
        else:
            return Polarity.UNCLEAR, 0.0, f'Cannot determine polarity: AE={ae_matches}, NO_AE={no_ae_matches}'
    
    @staticmethod
    def determine_strength(event: ExperienceEvent, polarity: Polarity) -> Tuple[int, Dict]:
        """
        Determine strength (0-2) based on data completeness and quality.
        
        PV Context:
        - Strength is the MAGNITUDE of the score
        - 0 = No data / very poor data
        - 1 = Weak / incomplete data
        - 2 = Strong / well-documented data
        
        Factors that increase strength:
        - Complete mandatory fields
        - Clinical context (indication, dosage)
        - Source credibility (doctor > pharmacy)
        - Temporal information (dates)
        - Outcome information
        
        Returns:
            Tuple of (strength, factors_dict)
        """
        if polarity == Polarity.UNCLEAR:
            return 0, {'reason': 'Unclear polarity, strength set to 0'}
        
        factors = {
            'has_drug_info': bool(event.drug_name),
            'has_patient_id': bool(event.patient_identifier_hash),
            'has_events': bool(event.observed_events),
            'has_indication': bool(event.indication),
            'has_dosage': bool(event.dosage),
            'has_dates': bool(event.event_date or event.start_date),
            'has_outcome': bool(event.outcome),
            'source_credibility': event.source.value if event.source else 'unknown'
        }
        
        # Calculate strength score
        score = 0
        
        # Mandatory fields (required for strength > 0)
        if factors['has_drug_info'] and factors['has_patient_id'] and factors['has_events']:
            score += 1
            
            # Additional factors for strength = 2
            additional_points = 0
            if factors['has_indication']:
                additional_points += 0.25
            if factors['has_dosage']:
                additional_points += 0.25
            if factors['has_dates']:
                additional_points += 0.25
            if factors['has_outcome']:
                additional_points += 0.25
            
            # Source credibility bonus
            if factors['source_credibility'] in ['doctor', 'hospital']:
                additional_points += 0.25
            
            if additional_points >= 0.75:
                score = 2
        
        factors['calculated_strength'] = score
        return score, factors
    
    @staticmethod
    def check_mandatory_fields(event: ExperienceEvent) -> Tuple[bool, List[str]]:
        """
        Check if all mandatory fields are present.
        
        PV Context:
        - Missing mandatory fields trigger follow-up requests
        - Data quality is critical for regulatory compliance
        
        Returns:
            Tuple of (has_all_fields, list_of_missing_fields)
        """
        missing = []
        
        if not event.drug_name:
            missing.append('drug_name')
        if not event.patient_identifier_hash:
            missing.append('patient_identifier_hash')
        if not event.observed_events:
            missing.append('observed_events')
        
        return len(missing) == 0, missing
    
    @classmethod
    def normalize_event(cls, event: ExperienceEvent, user=None) -> NormalizedExperience:
        """
        Create a normalized experience from a raw event.
        
        PV Context:
        - This is the main entry point for normalization
        - Creates the normalized record with polarity, strength, and score
        - Checks for missing mandatory fields
        
        Args:
            event: The raw experience event
            user: The user performing the action (for audit)
        
        Returns:
            NormalizedExperience object (not committed)
        """
        # Normalize drug and patient info
        drug_normalized = cls.normalize_drug_name(event.drug_name)
        patient_normalized = cls.normalize_patient_identifier(event.patient_identifier_hash)
        
        # Determine polarity
        polarity, confidence, reasoning = cls.determine_polarity(
            event.observed_events,
            event.outcome
        )
        
        # Determine strength
        strength, strength_factors = cls.determine_strength(event, polarity)
        
        # Check mandatory fields
        has_mandatory, missing_fields = cls.check_mandatory_fields(event)
        
        # Create normalized experience
        normalized = NormalizedExperience(
            event_id=event.id,
            drug_name_normalized=drug_normalized,
            patient_identifier_normalized=patient_normalized,
            polarity=polarity,
            polarity_confidence=confidence,
            polarity_reasoning=reasoning,
            strength=strength,
            strength_factors=strength_factors,
            has_mandatory_fields=has_mandatory,
            missing_fields=missing_fields if missing_fields else None,
            normalized_by='auto',
            normalization_version=cls.ALGORITHM_VERSION
        )
        
        # Calculate score
        normalized.calculate_score()
        
        db.session.add(normalized)
        
        return normalized
