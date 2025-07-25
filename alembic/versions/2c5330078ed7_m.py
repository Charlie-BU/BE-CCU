"""m

Revision ID: 2c5330078ed7
Revises: 041070409a84
Create Date: 2025-02-18 17:46:08.760229

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2c5330078ed7'
down_revision: Union[str, None] = '041070409a84'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('chemical', schema=None) as batch_op:
        batch_op.alter_column('type',
               existing_type=sa.INTEGER(),
               nullable=True)

    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('chemical', schema=None) as batch_op:
        batch_op.alter_column('type',
               existing_type=sa.INTEGER(),
               nullable=False)

    # ### end Alembic commands ###
