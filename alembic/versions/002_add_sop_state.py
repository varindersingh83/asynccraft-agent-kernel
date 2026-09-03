"""Add SOP run state tracking table.

Revision ID: 002
Revises: 001
Create Date: 2026-09-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add SOP run state tracking."""
    op.create_table(
        'sop_run_states',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('current_step_id', sa.String(length=64), nullable=True),
        sa.Column('completed_steps', sa.JSON(), nullable=False),
        sa.Column('events', sa.JSON(), nullable=False),
        sa.Column('is_complete', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['agent_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('run_id')
    )


def downgrade() -> None:
    """Remove SOP run state tracking."""
    op.drop_table('sop_run_states')
