"""file_tables

Revision ID: f3dc7e8a9d3a
Revises: 3d8ba25783a7
Create Date: 2022-10-21 23:00:17.545248

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f3dc7e8a9d3a"
down_revision = "3d8ba25783a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "video_properties",
        sa.Column("duration", sa.Integer(), nullable=False),
    )
    op.add_column(
        "video_properties",
        sa.Column("video_content_type", sa.String(length=200), nullable=False),
    )
    op.add_column(
        "video_properties",
        sa.Column("audio_content_type", sa.String(length=200), nullable=True),
    )
    op.drop_column("video_properties", "length")
    op.add_column(
        "videos",
        sa.Column("video_key", sa.String(length=1000), nullable=False),
    )
    op.add_column(
        "videos",
        sa.Column("audio_key", sa.String(length=1000), nullable=True),
    )
    op.drop_column("videos", "audio_path")
    op.drop_column("videos", "video_path")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "videos",
        sa.Column(
            "video_path",
            sa.VARCHAR(length=1000),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "videos",
        sa.Column(
            "audio_path",
            sa.VARCHAR(length=1000),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.drop_column("videos", "audio_key")
    op.drop_column("videos", "video_key")
    op.add_column(
        "video_properties",
        sa.Column("length", sa.INTEGER(), autoincrement=False, nullable=False),
    )
    op.drop_column("video_properties", "audio_content_type")
    op.drop_column("video_properties", "video_content_type")
    op.drop_column("video_properties", "duration")
    # ### end Alembic commands ###
