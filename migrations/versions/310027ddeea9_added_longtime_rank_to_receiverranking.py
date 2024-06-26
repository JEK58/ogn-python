"""Added longtime_rank to ReceiverRanking

Revision ID: 310027ddeea9
Revises: eb571174e4b2
Create Date: 2020-12-04 22:11:31.958278

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '310027ddeea9'
down_revision = 'eb571174e4b2'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('receiver_rankings', sa.Column('longtime_local_rank', sa.Integer(), nullable=True))
    op.add_column('receiver_rankings', sa.Column('longtime_local_rank_delta', sa.Integer(), nullable=True))
    op.add_column('receiver_rankings', sa.Column('longtime_global_rank', sa.Integer(), nullable=True))
    op.add_column('receiver_rankings', sa.Column('longtime_global_rank_delta', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('receiver_rankings', 'longtime_global_rank_delta')
    op.drop_column('receiver_rankings', 'longtime_global_rank')
    op.drop_column('receiver_rankings', 'longtime_local_rank_delta')
    op.drop_column('receiver_rankings', 'longtime_local_rank')
    # ### end Alembic commands ###
