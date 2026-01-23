"""
Adverse Event model - detailed AE information when polarity is AE.
Contains severity, causality, and outcome information.
"""
import enum
from datetime import datetime
from . import db


class Severity(enum.Enum):
    """
    Severity levels for adverse events.
    Based on standard PV classifications.
    """
    MILD = 'mild'
    MODERATE = 'moderate'
    SEVERE = 'severe'
    LIFE_THREATENING = 'life_threatening'
    FATAL = 'fatal'


class Outcome(enum.Enum):
    """
    Outcome of the adverse event.
    """
    RECOVERED = 'recovered'
    RECOVERING = 'recovering'
    NOT_RECOVERED = 'not_recovered'
    RECOVERED_WITH_SEQUELAE = 'recovered_with_sequelae'
    FATAL = 'fatal'
    UNKNOWN = 'unknown'


class AdverseEvent(db.Model):
    """
    Detailed adverse event information.
    
    PV Context:
    - Created when normalized experience has AE polarity
    - Contains clinical details needed for regulatory reporting
    - Severity and causality are key for case prioritization
    """
    __tablename__ = 'adverse_events'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Link to case and normalized experience
    case_id = db.Column(db.Integer, db.ForeignKey('case_master.id'), nullable=False, index=True)
    normalized_experience_id = db.Column(db.Integer, db.ForeignKey('normalized_experiences.id'))
    
    # AE details
    ae_description = db.Column(db.Text, nullable=False)
    
    # MedDRA coding
    meddra_pt_code = db.Column(db.String(20))
    meddra_pt_term = db.Column(db.String(255))
    meddra_llt_code = db.Column(db.String(20))  # Lowest Level Term
    meddra_llt_term = db.Column(db.String(255))
    
    # Severity assessment
    severity = db.Column(db.Enum(Severity))
    severity_notes = db.Column(db.Text)
    
    # Seriousness criteria (for regulatory purposes)
    results_in_death = db.Column(db.Boolean, default=False)
    life_threatening = db.Column(db.Boolean, default=False)
    requires_hospitalization = db.Column(db.Boolean, default=False)
    prolongs_hospitalization = db.Column(db.Boolean, default=False)
    results_in_disability = db.Column(db.Boolean, default=False)
    congenital_anomaly = db.Column(db.Boolean, default=False)
    other_medically_important = db.Column(db.Boolean, default=False)
    
    # Dates
    onset_date = db.Column(db.Date)
    resolution_date = db.Column(db.Date)
    
    # Outcome
    outcome = db.Column(db.Enum(Outcome))
    outcome_date = db.Column(db.Date)
    
    # Causality assessment
    causality_assessment = db.Column(db.String(50))  # certain, probable, possible, unlikely, unrelated
    causality_method = db.Column(db.String(50))  # WHO-UMC, Naranjo, etc.
    causality_score = db.Column(db.Float)
    causality_notes = db.Column(db.Text)
    
    # Action taken with drug
    action_taken = db.Column(db.String(50))  # withdrawn, dose_reduced, dose_not_changed, unknown
    
    # Rechallenge/Dechallenge
    dechallenge_result = db.Column(db.String(50))  # positive, negative, not_done, unknown
    rechallenge_result = db.Column(db.String(50))  # positive, negative, not_done, unknown
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Soft delete
    is_deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime)
    
    # Relationships
    case = db.relationship('CaseMaster', backref='adverse_events')
    normalized_experience = db.relationship('NormalizedExperience', backref='adverse_event', uselist=False)
    
    def is_serious(self):
        """
        Determine if this AE meets seriousness criteria.
        Any of these makes the AE serious for regulatory purposes.
        """
        return any([
            self.results_in_death,
            self.life_threatening,
            self.requires_hospitalization,
            self.prolongs_hospitalization,
            self.results_in_disability,
            self.congenital_anomaly,
            self.other_medically_important
        ])
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'case_id': self.case_id,
            'ae_description': self.ae_description,
            'meddra_pt_term': self.meddra_pt_term,
            'severity': self.severity.value if self.severity else None,
            'outcome': self.outcome.value if self.outcome else None,
            'causality_assessment': self.causality_assessment,
            'is_serious': self.is_serious(),
            'onset_date': self.onset_date.isoformat() if self.onset_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
