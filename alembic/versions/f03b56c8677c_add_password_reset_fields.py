"""add password reset fields

Revision ID: f03b56c8677c
Revises:
Create Date: 2026-08-16 21:08:45.784244
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f03b56c8677c'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('reset_token', sa.String(), nullable=True)
    )

    op.add_column(
        'users',
        sa.Column('reset_token_expires', sa.DateTime(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('users', 'reset_token_expires')
    op.drop_column('users', 'reset_token')

    