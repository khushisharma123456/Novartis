"""
Normalized Experience model - structured/cleaned version of experience events.
Normalization is essential for consistent scoring and case linking.
"""
import enum
from datetime import datetime
from . import db


class Polarity(enum.Enum):
    """
    Polarity of the experience event.
    
    PV Context:
    - AE (Adverse Event): Negative experience, potential safety signal
    - NO_AE: Positive experience, no adverse event observed
    - UNCLEAR: Data is insufficient to determine polarity
    
    Polarity is a key factor in the scoring formula:
    Score = Polarity × Strength
    """
    AE = 'ae'           # Adverse Event detected
    NO_AE = 'no_ae'     # No Adverse Event
    UNCLEAR = 'unclear' # Cannot determine from available data


class NormalizedExperience(db.Model):
    """
    Normalized/structured version of experience event.
    
    PV Context:
    - Raw events are normalized for consistent analysis
    - MedDRA coding is applied for standardization
    - Normalization enables case linking and scoring
    """
    __tablename__ = 'normalized_experiences'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Link to original event
    event_id = db.Column(db.Integer, db.ForeignKey('experience_events.id'), nullable=False, unique=True)
    
    # Normalized drug information
    drug_name_normalized = db.Column(db.String(255), index=True)
    drug_active_ingredient = db.Column(db.String(255))
    atc_code = db.Column(db.String(20))  # ATC classification
    
    # Normalized patient identifier
    patient_identifier_normalized = db.Column(db.String(255), index=True)
    
    # MedDRA coding for adverse events
    # Preferred Term (PT) and System Organ Class (SOC)
    meddra_pt_code = db.Column(db.String(20))   # MedDRA Preferred Term code
    meddra_pt_term = db.Column(db.String(255))  # MedDRA Preferred Term text
    meddra_soc_code = db.Column(db.String(20))  # MedDRA System Organ Class code
    meddra_soc_term = db.Column(db.String(255)) # MedDRA System Organ Class text
    
    # Polarity determination
    # This is CRITICAL for scoring: AE = negative, NO_AE = positive
    polarity = db.Column(db.Enum(Polarity), nullable=False, default=Polarity.UNCLEAR)
    polarity_confidence = db.Column(db.Float, default=0.0)  # 0.0 to 1.0
    polarity_reasoning = db.Column(db.Text)  # Why this polarity was assigned
    
    # Strength determination (0 to 2)
    # Affects score magnitude: 0 = no data, 1 = weak, 2 = strong
    strength = db.Column(db.Integer, default=0)  # 0, 1, or 2
    strength_factors = db.Column(db.JSON)  # Factors that contributed to strength
    
    # Computed score (polarity × strength)
    # Range: -2 to +2
    computed_score = db.Column(db.Float, default=0.0)
    
    # Data quality flags
    has_mandatory_fields = db.Column(db.Boolean, default=False)
    missing_fields = db.Column(db.JSON)  # List of missing mandatory fields
    data_quality_notes = db.Column(db.Text)
    
    # Normalization metadata
    normalized_by = db.Column(db.String(50))  # 'auto', 'manual', 'ai'
    normalization_version = db.Column(db.String(20))  # Algorithm version
    
    # Human override (CRITICAL: allows human to override automated decisions)
    is_overridden = db.Column(db.Boolean, default=False)
    override_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    override_reason = db.Column(db.Text)
    override_at = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Soft delete
    is_deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime)
    
    # Relationships
    event = db.relationship('ExperienceEvent', backref='normalized', uselist=False)
    override_by = db.relationship('User', backref='overridden_normalizations')
    
    def calculate_score(self):
        """
        Calculate the score based on polarity and strength.
        
        Score Formula: Polarity × Strength
        - AE polarity = -1 (negative)
        - NO_AE polarity = +1 (positive)
        - UNCLEAR polarity = 0 (neutral)
        
        Returns: Score between -2 and +2
        """
        polarity_multiplier = {
            Polarity.AE: -1,
            Polarity.NO_AE: 1,
            Polarity.UNCLEAR: 0
        }
        
        multiplier = polarity_multiplier.get(self.polarity, 0)
        self.computed_score = multiplier * self.strength
        return self.computed_score
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'event_id': self.event_id,
            'drug_name_normalized': self.drug_name_normalized,
            'meddra_pt_term': self.meddra_pt_term,
            'meddra_soc_term': self.meddra_soc_term,
            'polarity': self.polarity.value if self.polarity else None,
            'polarity_confidence': self.polarity_confidence,
            'strength': self.strength,
            'computed_score': self.computed_score,
            'has_mandatory_fields': self.has_mandatory_fields,
            'missing_fields': self.missing_fields,
            'is_overridden': self.is_overridden,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
