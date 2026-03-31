from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Commit(Base):
    __tablename__ = "commits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repo_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("repositories.id", ondelete="SET NULL"), nullable=True
    )
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    author_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    author_email: Mapped[str | None] = mapped_column(String(100), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )

    repository: Mapped["Repository"] = relationship(  # noqa: F821
        "Repository", back_populates="commits", lazy="noload"
    )
    files: Mapped[list["CommitFile"]] = relationship(
        "CommitFile", back_populates="commit", lazy="noload", cascade="all, delete-orphan"
    )


class CommitFile(Base):
    __tablename__ = "commit_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    commit_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("commits.id", ondelete="CASCADE"), nullable=True
    )
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    change_type: Mapped[str | None] = mapped_column(String(10), nullable=True)
    additions: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    deletions: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)

    commit: Mapped["Commit"] = relationship("Commit", back_populates="files", lazy="noload")
