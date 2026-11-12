from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, JSON, LargeBinary, Text
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

class Account(Base):
    __tablename__='accounts'
    id: Mapped[str]=mapped_column(String, primary_key=True)
    account_type: Mapped[str]=mapped_column(String)
    label: Mapped[int]=mapped_column(Integer, default=0)
    gnn_probability: Mapped[float]=mapped_column(Float, default=0)
    rule_score: Mapped[float]=mapped_column(Float, default=0)
    final_risk: Mapped[float]=mapped_column(Float, default=0)
    risk_level: Mapped[str]=mapped_column(String, default='Low')
    features: Mapped[dict]=mapped_column(JSON, default=dict)

class Transaction(Base):
    __tablename__='transactions'
    id: Mapped[str]=mapped_column(String, primary_key=True)
    source_id: Mapped[str]=mapped_column(ForeignKey('accounts.id'))
    target_id: Mapped[str]=mapped_column(ForeignKey('accounts.id'))
    amount: Mapped[float]=mapped_column(Float)
    timestamp: Mapped[datetime]=mapped_column(DateTime)
    transaction_type: Mapped[str]=mapped_column(String)
    scenario: Mapped[str]=mapped_column(String)

class Prediction(Base):
    __tablename__='predictions'
    id: Mapped[int]=mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[str]=mapped_column(ForeignKey('accounts.id'))
    probability: Mapped[float]=mapped_column(Float)
    final_risk: Mapped[float]=mapped_column(Float)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class Alert(Base):
    __tablename__='alerts'
    id: Mapped[str]=mapped_column(String, primary_key=True)
    account_ids: Mapped[list]=mapped_column(JSON)
    transaction_ids: Mapped[list]=mapped_column(JSON)
    pattern_type: Mapped[str]=mapped_column(String)
    amount: Mapped[float]=mapped_column(Float)
    timestamp: Mapped[datetime]=mapped_column(DateTime)
    risk_level: Mapped[str]=mapped_column(String)
    explanation: Mapped[str]=mapped_column(String)

class TrainingRun(Base):
    __tablename__='training_runs'
    id: Mapped[int]=mapped_column(Integer, primary_key=True, autoincrement=True)
    status: Mapped[str]=mapped_column(String)
    started_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime|None]=mapped_column(DateTime, nullable=True)
    metrics: Mapped[dict]=mapped_column(JSON, default=dict)
    error: Mapped[str|None]=mapped_column(String, nullable=True)

class ModelArtifact(Base):
    """Versioned CPU model/checkpoint and preprocessing payloads stored in the database."""
    __tablename__='model_artifacts'
    id: Mapped[int]=mapped_column(Integer, primary_key=True, autoincrement=True)
    version: Mapped[str]=mapped_column(String, unique=True, index=True)
    status: Mapped[str]=mapped_column(String, default='active')
    model_blob: Mapped[bytes]=mapped_column(LargeBinary)
    scaler_blob: Mapped[bytes]=mapped_column(LargeBinary)
    metrics: Mapped[dict]=mapped_column(JSON, default=dict)
    configuration: Mapped[dict]=mapped_column(JSON, default=dict)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)
