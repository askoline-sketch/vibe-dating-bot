from datetime import datetime
from sqlalchemy import (
    BigInteger, String, Integer, Boolean, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.db import Base


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(64))
    age: Mapped[int] = mapped_column(Integer)
    gender: Mapped[str] = mapped_column(String(10))  # 'male' / 'female'
    looking_for: Mapped[str] = mapped_column(String(10))  # 'male' / 'female' / 'any'
    city: Mapped[str] = mapped_column(String(64))
    bio: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    photos = relationship(
        'Photo', back_populates='user', cascade='all, delete-orphan'
    )


class Photo(Base):
    __tablename__ = 'photos'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE')
    )
    file_id: Mapped[str] = mapped_column(String(255))
    position: Mapped[int] = mapped_column(Integer, default=0)

    user = relationship('User', back_populates='photos')


class Like(Base):
    __tablename__ = 'likes'

    id: Mapped[int] = mapped_column(primary_key=True)
    from_user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE')
    )
    to_user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE')
    )
    is_super: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Match(Base):
    __tablename__ = 'matches'

    id: Mapped[int] = mapped_column(primary_key=True)
    user1_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE')
    )
    user2_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE')
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Message(Base):
    __tablename__ = 'messages'

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey('matches.id', ondelete='CASCADE')
    )
    from_user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE')
    )
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Subscription(Base):
    __tablename__ = 'subscriptions'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE')
    )
    plan: Mapped[str] = mapped_column(String(20))  # 'month', 'half_year'
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    payment_id: Mapped[str] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

from datetime import date
from sqlalchemy import Date


class DailyUsage(Base):
    __tablename__ = 'daily_usage'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE')
    )
    date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    superlikes: Mapped[int] = mapped_column(Integer, default=0)
    messages: Mapped[int] = mapped_column(Integer, default=0)

class View(Base):
    __tablename__ = 'views'

    id: Mapped[int] = mapped_column(primary_key=True)
    from_user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE')
    )
    to_user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE')
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )