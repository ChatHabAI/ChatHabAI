"""add limit and is_premium fields

Revision ID: 26191f1ef65c
Revises: cc2d716a2b80
Create Date: 2023-12-29 21:39:53.634200

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy.sql import expression
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '26191f1ef65c'
down_revision: Union[str, None] = 'cc2d716a2b80'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('is_premium', sa.Boolean(), nullable=True, server_default=expression.false()))
    op.add_column('users', sa.Column('available_gpt_requests', sa.Integer(), nullable=True, server_default=sa.text('3')))
    op.add_column('users', sa.Column('available_image_requests', sa.Integer(), nullable=True, server_default=sa.text('3')))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'available_image_requests')
    op.drop_column('users', 'available_gpt_requests')
    op.drop_column('users', 'is_premium')
    # ### end Alembic commands ###
