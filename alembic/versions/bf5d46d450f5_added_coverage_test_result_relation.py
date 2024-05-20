"""added coverage/test_result relation

Revision ID: bf5d46d450f5
Revises: 7f8df6212797
Create Date: 2024-05-19 23:59:00.090831

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bf5d46d450f5'
down_revision: Union[str, None] = '7f8df6212797'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('augment_test_results', 'cov_plus')
    op.add_column('coverage', sa.Column('test_result', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'coverage', 'augment_test_results', ['test_result'], ['id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'coverage', type_='foreignkey')
    op.drop_column('coverage', 'test_result')
    op.add_column('augment_test_results', sa.Column('cov_plus', sa.INTEGER(), autoincrement=False, nullable=True))
    # ### end Alembic commands ###
