"""
Case Scoring Service - Quality Assessment & Strength Evaluation
Implements STEP 7, 8, 9 of the quality assessment framework
"""

from datetime import datetime, timedelta


class CaseScoringEngine:
    """
    Evaluates case quality and calculates confidence-weighted scores
    Final Score = Polarity × Strength
    """
    
    # Mandatory fields for case completeness
    MANDATORY_FIELDS = [
        'name', 'age', 'gender', 'drug_name', 
        'symptoms', 'created_at', 'created_by'
    ]
    
    def __init__(self):
        pass
    
    # ===== STEP 7: CASE STRENGTH EVALUATION =====
    
    def evaluate_case_strength(self, case):
        """
        Evaluate the overall strength of a case based on data quality
        
        Args:
            case: Patient model instance
            
        Returns:
            dict: {
                'strength_level': 'Low'|'Medium'|'High',
                'strength_score': 0|1|2,
                'breakdown': {
                    'completeness': float (0-1),
                    'temporal_clarity': float (0-1),
                    'medical_confirmation': float (0-1),
                    'followup_responsiveness': float (0-1)
                },
                'confidence': str ('Very Low' to 'Very High')
            }
        """
        
        # Evaluate each factor
        completeness = self._evaluate_completeness(case)
        temporal = self._evaluate_temporal_clarity(case)
        medical = self._evaluate_medical_confirmation(case)
        followup = self._evaluate_followup_responsiveness(case)
        
        # Weighted average (30% each for first three, 10% for last)
        weighted_score = (
            completeness * 0.3 +
            temporal * 0.3 +
            medical * 0.2 +
            followup * 0.2
        )
        
        # Map to strength levels
        if weighted_score >= 0.67:
            strength_level = 'High'
            strength_score = 2
        elif weighted_score >= 0.33:
            strength_level = 'Medium'
            strength_score = 1
        else:
            strength_level = 'Low'
            strength_score = 0
        
        # Update case in database
        case.strength_level = strength_level
        case.strength_score = strength_score
        case.completeness_score = completeness
        case.temporal_clarity_score = temporal
        case.medical_confirmation_score = medical
        case.followup_responsiveness_score = followup
        case.evaluated_at = datetime.utcnow()
        
        return {
            'strength_level': strength_level,
            'strength_score': strength_score,
            'overall_score': round(weighted_score, 3),
            'breakdown': {
                'completeness': round(completeness, 3),
                'temporal_clarity': round(temporal, 3),
                'medical_confirmation': round(medical, 3),
                'followup_responsiveness': round(followup, 3)
            },
            'confidence': self._get_confidence_level(weighted_score)
        }
    
    def _evaluate_completeness(self, case):
        """
        Assess what % of mandatory fields are filled
        
        Score: 0-1 (0% to 100%)
        """
        filled_count = 0
        for field in self.MANDATORY_FIELDS:
            value = getattr(case, field, None)
            if value is not None and str(value).strip():
                filled_count += 1
        
        completeness = filled_count / len(self.MANDATORY_FIELDS)
        case.mandatory_fields_filled = filled_count
        case.total_mandatory_fields = len(self.MANDATORY_FIELDS)
        
        return completeness
    
    def _evaluate_temporal_clarity(self, case):
        """
        Check if the timeline of the case is clear
        
        Score: 
        - 1.0: Both onset and resolution dates available
        - 0.7: Only onset date available
        - 0.5: Only creation date available
        - 0.0: No timeline information
        """
        if case.symptom_onset_date and case.symptom_resolution_date:
            case.has_clear_timeline = True
            return 1.0
        elif case.symptom_onset_date:
            case.has_clear_timeline = True
            return 0.7
        elif case.created_at:
            return 0.5
        return 0.0
    
    def _evaluate_medical_confirmation(self, case):
        """
        Check if case has been confirmed by medical professionals
        
        Score:
        - 1.0: Hospital confirmed
        - 0.7: Doctor confirmed
        - 0.0: No confirmation
        """
        if case.hospital_confirmed:
            return 1.0
        elif case.doctor_confirmed:
            return 0.7
        return 0.0
    
    def _evaluate_followup_responsiveness(self, case):
        """
        Assess quality of follow-up responses
        
        Score:
        - 1.0: Good quality responses
        - 0.6: Fair quality responses
        - 0.2: Poor quality responses
        - 0.0: No follow-up responses yet
        """
        if case.followup_response_quality == 'Good':
            return 1.0
        elif case.followup_response_quality == 'Fair':
            return 0.6
        elif case.followup_response_quality == 'Poor':
            return 0.2
        return 0.0
    
    def _get_confidence_level(self, score):
        """Convert strength score to confidence level"""
        if score >= 0.9:
            return 'Very High'
        elif score >= 0.75:
            return 'High'
        elif score >= 0.6:
            return 'Medium'
        elif score >= 0.4:
            return 'Low'
        else:
            return 'Very Low'
    
    # ===== STEP 8: FINAL CASE SCORING =====
    
    def calculate_final_score(self, case):
        """
        Calculate Final Score = Polarity × Strength
        
        This produces confidence-weighted experience scores:
        -2: Strong Adverse Event (AE) - High confidence negative
        -1: Weak AE - Low/medium confidence adverse
         0: Unclear/Cannot assess - Missing critical data
        +1: Moderate positive - Some evidence of non-adverse
        +2: Strong positive - High confidence non-adverse
        
        Args:
            case: Patient model instance (should have strength_score already calculated)
            
        Returns:
            dict: {
                'case_score': -2 to 2,
                'polarity': -1|0|+1,
                'strength': 0|1|2,
                'interpretation': str,
                'confidence': str
            }
        """
        
        # Ensure strength is evaluated
        if case.strength_score is None:
            strength_info = self.evaluate_case_strength(case)
            strength = strength_info['strength_score']
        else:
            strength = case.strength_score
        
        # Determine polarity
        polarity = self._determine_polarity(case)
        
        # Calculate final score
        final_score = polarity * strength
        
        # Get interpretation
        interpretation = self._interpret_score(final_score)
        
        # Update case
        case.polarity = polarity
        case.case_score = final_score
        case.case_score_interpretation = interpretation
        case.case_score_calculated_at = datetime.utcnow()
        
        return {
            'case_score': final_score,
            'polarity': polarity,
            'strength': strength,
            'interpretation': interpretation,
            'confidence': self._get_score_confidence(final_score),
            'polarity_text': self._polarity_to_text(polarity)
        }
    
    def _determine_polarity(self, case):
        """
        Determine case polarity:
        -1: Adverse Event (negative experience)
         0: Unclear / Inconclusive
        +1: Positive / Non-adverse experience
        
        Logic: Determined by risk level
        """
        if case.risk_level in ['High', 'Medium']:
            # High/Medium risk = Adverse Event
            return -1
        elif case.risk_level == 'Low':
            # Low risk = Positive (non-adverse)
            return 1
        else:
            # Unknown/unclear
            return 0
    
    def _polarity_to_text(self, polarity):
        """Convert polarity value to text"""
        if polarity == -1:
            return 'Adverse Event'
        elif polarity == 0:
            return 'Unclear'
        elif polarity == 1:
            return 'Positive'
        return 'Unknown'
    
    def _interpret_score(self, score):
        """Get human-readable interpretation of score"""
        interpretations = {
            -2: 'Strong Adverse Event - Very High Confidence',
            -1: 'Weak/Unclear Adverse Event - Needs Review',
             0: 'Cannot Assess - Missing Critical Data',
            +1: 'Likely Non-Adverse - Needs Confirmation',
            +2: 'Strong Non-Adverse Event - Very High Confidence'
        }
        return interpretations.get(score, 'Unknown Score')
    
    def _get_score_confidence(self, score):
        """Get confidence level for a case score"""
        if score in [-2, 2]:
            return 'Very High'
        elif score in [-1, 1]:
            return 'Medium'
        else:
            return 'Low'
    
    # ===== STEP 9: FOLLOW-UP TRACKING =====
    
    def check_followup_triggers(self, case):
        """
        Check if case triggers follow-up requirements
        
        Triggers:
        - Score = 0 (unclear)
        - Strength < 2 and Adverse Event (weak AE)
        - Completeness < 70%
        - No medical confirmation
        
        Returns:
            dict: {
                'follow_up_required': bool,
                'triggers': [list of trigger reasons],
                'priority': 'low'|'medium'|'high'|'critical'
            }
        """
        triggers = []
        
        # Trigger 1: Case score is unclear
        if case.case_score == 0:
            triggers.append('unclear_score')
        
        # Trigger 2: Weak adverse event
        if case.strength_score < 2 and case.polarity == -1:
            triggers.append('weak_ae')
        
        # Trigger 3: Low completeness
        if case.completeness_score and case.completeness_score < 0.7:
            triggers.append('low_completeness')
        
        # Trigger 4: No medical confirmation for AE
        if case.polarity == -1 and not case.doctor_confirmed and not case.hospital_confirmed:
            triggers.append('no_medical_confirmation')
        
        # Determine priority
        priority = self._determine_priority(triggers)
        
        # Update case
        case.follow_up_required = len(triggers) > 0
        
        return {
            'follow_up_required': len(triggers) > 0,
            'triggers': triggers,
            'priority': priority,
            'trigger_descriptions': self._describe_triggers(triggers)
        }
    
    def _determine_priority(self, triggers):
        """Determine follow-up priority based on triggers"""
        critical_triggers = ['unclear_score', 'weak_ae', 'no_medical_confirmation']
        
        if any(t in critical_triggers for t in triggers):
            if 'weak_ae' in triggers and 'no_medical_confirmation' in triggers:
                return 'critical'
            return 'high'
        elif 'low_completeness' in triggers:
            return 'medium'
        return 'low'
    
    def _describe_triggers(self, triggers):
        """Convert triggers to human-readable descriptions"""
        descriptions = {
            'unclear_score': 'Case score cannot be determined - insufficient data',
            'weak_ae': 'Weak adverse event - needs additional confirmation',
            'low_completeness': 'Missing important case information (< 70% complete)',
            'no_medical_confirmation': 'Adverse event not confirmed by medical professional'
        }
        return {t: descriptions.get(t, t) for t in triggers}


# Utility functions

def evaluate_case(case):
    """Convenience function to evaluate case strength"""
    engine = CaseScoringEngine()
    return engine.evaluate_case_strength(case)


def score_case(case):
    """Convenience function to calculate final case score"""
    engine = CaseScoringEngine()
    return engine.calculate_final_score(case)


def check_followup(case):
    """Convenience function to check follow-up triggers"""
    engine = CaseScoringEngine()
    return engine.check_followup_triggers(case)
