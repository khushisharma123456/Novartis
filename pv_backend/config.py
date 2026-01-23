"""
Configuration for the Pharmacovigilance Backend Service.
Supports PostgreSQL for production and SQLite for development/testing.
"""
import os
from datetime import timedelta

class Config:
    """Base configuration class."""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'pv-secret-key-change-in-production')
    
    # Database - PostgreSQL for production, SQLite for development
    # For PostgreSQL: postgresql://user:password@localhost:5432/pv_database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 
        'sqlite:///pv_database.db'  # Default to SQLite for development
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,  # Enable connection health checks
    }
    
    # JWT settings
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # PV-specific settings
    # Score ranges: -2 to +2
    # -2 = Strong, well-documented AE
    # -1 = Weak/incomplete AE
    #  0 = Poor or unclear data
    # +1 = Moderate positive/no-AE experience
    # +2 = Strong, confirmed positive experience
    MIN_SCORE = -2
    MAX_SCORE = 2
    
    # Follow-up trigger thresholds
    FOLLOW_UP_SCORE_THRESHOLD = 0  # Trigger if score is 0
    FOLLOW_UP_AE_STRENGTH_THRESHOLD = 2  # Trigger if AE polarity but strength < 2


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_ECHO = True  # Log SQL queries


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SQLALCHEMY_ECHO = False


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
