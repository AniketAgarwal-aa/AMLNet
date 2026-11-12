"""initial AMLNet schema

Revision ID: 0001_initial
"""
from alembic import op
import sqlalchemy as sa
revision='0001_initial'
down_revision=None
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('accounts',sa.Column('id',sa.String(),primary_key=True),sa.Column('account_type',sa.String(),nullable=False),sa.Column('label',sa.Integer(),nullable=False),sa.Column('gnn_probability',sa.Float(),nullable=False),sa.Column('rule_score',sa.Float(),nullable=False),sa.Column('final_risk',sa.Float(),nullable=False),sa.Column('risk_level',sa.String(),nullable=False),sa.Column('features',sa.JSON(),nullable=False))
    op.create_table('transactions',sa.Column('id',sa.String(),primary_key=True),sa.Column('source_id',sa.String(),sa.ForeignKey('accounts.id'),nullable=False),sa.Column('target_id',sa.String(),sa.ForeignKey('accounts.id'),nullable=False),sa.Column('amount',sa.Float(),nullable=False),sa.Column('timestamp',sa.DateTime(),nullable=False),sa.Column('transaction_type',sa.String(),nullable=False),sa.Column('scenario',sa.String(),nullable=False))
    op.create_table('predictions',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('account_id',sa.String(),sa.ForeignKey('accounts.id'),nullable=False),sa.Column('probability',sa.Float(),nullable=False),sa.Column('final_risk',sa.Float(),nullable=False),sa.Column('created_at',sa.DateTime(),nullable=False))
    op.create_table('alerts',sa.Column('id',sa.String(),primary_key=True),sa.Column('account_ids',sa.JSON(),nullable=False),sa.Column('transaction_ids',sa.JSON(),nullable=False),sa.Column('pattern_type',sa.String(),nullable=False),sa.Column('amount',sa.Float(),nullable=False),sa.Column('timestamp',sa.DateTime(),nullable=False),sa.Column('risk_level',sa.String(),nullable=False),sa.Column('explanation',sa.String(),nullable=False))
    op.create_table('training_runs',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('status',sa.String(),nullable=False),sa.Column('started_at',sa.DateTime(),nullable=False),sa.Column('completed_at',sa.DateTime(),nullable=True),sa.Column('metrics',sa.JSON(),nullable=False),sa.Column('error',sa.String(),nullable=True))
    op.create_table('model_artifacts',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('version',sa.String(),nullable=False),sa.Column('status',sa.String(),nullable=False),sa.Column('model_blob',sa.LargeBinary(),nullable=False),sa.Column('scaler_blob',sa.LargeBinary(),nullable=False),sa.Column('metrics',sa.JSON(),nullable=False),sa.Column('configuration',sa.JSON(),nullable=False),sa.Column('created_at',sa.DateTime(),nullable=False))
    op.create_index('ix_model_artifacts_version','model_artifacts',['version'],unique=True)

def downgrade():
    op.drop_table('model_artifacts');op.drop_table('training_runs');op.drop_table('alerts');op.drop_table('predictions');op.drop_table('transactions');op.drop_table('accounts')
