from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class VOD(Base):
    __tablename__ = 'vods'
    id = Column(Integer, primary_key=True)
    twitch_id = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    category = Column(String)
    url = Column(String)
    created_at = Column(DateTime)
    type = Column(String)

    youtube_links = relationship('YouTubeLink', back_populates='vod', cascade="all, delete-orphan")
    clips = relationship('Clip', back_populates='vod', cascade="all, delete-orphan")

class YouTubeLink(Base):
    __tablename__ = 'youtube_links'
    id = Column(Integer, primary_key=True)
    url = Column(String, nullable=False)
    title = Column(String)
    video_id = Column(String)
    vod_id = Column(Integer, ForeignKey('vods.id'))
    vod = relationship('VOD', back_populates='youtube_links')

class Clip(Base):
    __tablename__ = 'clips'
    id = Column(Integer, primary_key=True)
    twitch_id = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    category = Column(String)
    url = Column(String)
    created_at = Column(DateTime)
    vod_id = Column(Integer, ForeignKey('vods.id'))
    vod = relationship('VOD', back_populates='clips')
    vod_twitch_id = Column(String)
    is_favorite = Column(Boolean, default=False)
    thumbnail_url = Column(String)
