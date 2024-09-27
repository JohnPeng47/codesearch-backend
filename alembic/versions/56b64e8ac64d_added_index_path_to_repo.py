"""added index path to repo

Revision ID: 56b64e8ac64d
Revises: cd6d4820e16b
Create Date: 2024-09-19 14:51:11.888535

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '56b64e8ac64d'
down_revision: Union[str, None] = 'cd6d4820e16b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('repos', sa.Column('index_path', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('repos', 'index_path')
    # ### end Alembic commands ###