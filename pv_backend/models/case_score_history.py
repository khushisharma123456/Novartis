"""
Case Score History model - tracks score evolution over time.
Scores are NEVER overwritten, only appended to history.
"""
from datetime import datetime
from . import db


class CaseScoreHistory(db.Model):
    """
    Score history for pharmacovigilance cases.
    
    PV Context:
    - Scores evolve as new evidence arrives
    - History is CRITICAL for audit and understanding case evolution
    - Score = Polarity × Strength (range: -2 to +2)
    - Never delete history records
    """
    __tablename__ = 'case_score_history'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Link to case
    case_id = db.Column(db.Integer, db.ForeignKey('case_master.id'), nullable=False, index=True)
    
    # Link to the event that triggered this score update
    triggered_by_event_id = db.Column(db.Integer, db.ForeignKey('experience_events.id'))
    
    # Score components
    polarity = db.Column(db.String(20), nullable=False)  # ae, no_ae, unclear
    strength = db.Column(db.Integer, nullable=False)     # 0, 1, or 2
    
    # Computed score (polarity × strength)
    score = db.Column(db.Float, nullable=False)
    
    # Previous score (for delta tracking)
    previous_score = db.Column(db.Float)
    score_delta = db.Column(db.Float)  # Change from previous score
    
    # Scoring reasoning (explainability)
    scoring_factors = db.Column(db.JSON)  # Factors that contributed to this score
    scoring_notes = db.Column(db.Text)    # Human-readable explanation
    
    # Scoring method
    scored_by = db.Column(db.String(50))  # 'auto', 'manual', 'ai'
    scoring_algorithm_version = db.Column(db.String(20))
    
    # Human override
    is_override = db.Column(db.Boolean, default=False)
    override_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    override_reason = db.Column(db.Text)
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    case = db.relationship('CaseMaster', backref='score_history')
    triggered_by_event = db.relationship('ExperienceEvent', backref='score_updates')
    override_by = db.relationship('User', backref='score_overrides')
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'case_id': self.case_id,
            'polarity': self.polarity,
            'strength': self.strength,
            'score': self.score,
            'previous_score': self.previous_score,
            'score_delta': self.score_delta,
            'scoring_factors': self.scoring_factors,
            'scoring_notes': self.scoring_notes,
            'is_override': self.is_override,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
