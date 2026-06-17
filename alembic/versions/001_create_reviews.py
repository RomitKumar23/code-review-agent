"""create reviews table

Revision ID: 001
Revises: 
Create Date: 2024-01-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'reviews',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('repo', sa.String(255), nullable=False),
        sa.Column('pr_number', sa.Integer, nullable=False),
        sa.Column('pr_title', sa.Text),
        sa.Column('status', sa.String(32), server_default='pending'),
        sa.Column('provider', sa.String(64), nullable=False),
        sa.Column('model', sa.String(128), nullable=False),
        sa.Column('comments', JSONB),
        sa.Column('summary', sa.Text),
        sa.Column('error', sa.Text),
        sa.Column('tokens_used', sa.Integer, server_default='0'),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime),
    )
    op.create_table(
        'provider_config',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('provider', sa.String(64), unique=True, nullable=False),
        sa.Column('model', sa.String(128), nullable=False),
        sa.Column('is_active', sa.String(1), server_default='0'),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('now()')),
    )


def downgrade():
    op.drop_table('provider_config')
    op.drop_table('reviews')
