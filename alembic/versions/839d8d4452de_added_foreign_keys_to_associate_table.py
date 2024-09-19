"""added foreign keys to associate table

Revision ID: 839d8d4452de
Revises: 43f0fea504a6
Create Date: 2024-09-19 00:34:41.028711

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '839d8d4452de'
down_revision: Union[str, None] = '43f0fea504a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('user_repo',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('repo_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['repo_id'], ['repos.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('user_id', 'repo_id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('user_repo')
    # ### end Alembic commands ###
