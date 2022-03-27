from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.types import Boolean, DateTime, Integer, String

Base = declarative_base()


#    Subreddit         Redditor
#         \            /      \
#          \          /        \
#           Submission     RedditorSnapshot
#               |
#               |
#            Comment

class Subreddit(Base):
    __tablename__ = "subreddit"

    created_utc = Column(DateTime)
    display_name = Column(String, primary_key=True)
    public_description = Column(String)
    subscribers = Column(Integer)
    over18 = Column(Boolean)
    submissions = relationship("Submission", back_populates="subreddit")

class Redditor(Base):
    __tablename__ = "redditor"

    name = Column(String, primary_key=True)
    created_utc = Column(DateTime)
    redditor_snapshots = relationship(
        "RedditorSnapshot", back_populates="redditor"
    )
    submissions = relationship(
        "Submission", back_populates="redditor"
    )
    comments = relationship(
        "Comment", back_populates="redditor"
    )

class RedditorSnapshot(Base):
    __tablename__ = "redditor_snapshot"

    redditor = relationship("Redditor", back_populates="redditor_snapshots")
    name = Column(String, ForeignKey("redditor.name"), primary_key=True)
    snapshot_utc = Column(DateTime, primary_key=True)
    link_karma = Column(Integer)
    comment_karma = Column(Integer)
    has_verified_email = Column(Boolean)
    subreddit_title = Column(String)
    subreddit_description = Column(String)
    subreddit_nsfw = Column(String)
    # TODO: estimated_age = Column(Integer)
    # TODO: estimated_gender = Column(String)

class Submission(Base):
    __tablename__ = "submission"

    id = Column(String, primary_key=True)
    created_utc = Column(DateTime)
    redditor_name = Column(String, ForeignKey("redditor.name"))
    redditor = relationship("Redditor", back_populates="submissions")
    subreddit_display_name = Column(String, ForeignKey("subreddit.display_name"))
    subreddit = relationship("Subreddit", back_populates="submissions")
    comments = relationship("Comment", back_populates="submission")
    title = Column(String)
    link_flair_text = Column(String)
    is_self = Column(Boolean)
    over_18 = Column(Boolean)
    selftext = Column(String)
    url = Column(String)
    # TODO: user_reports = Column(String)
    # TODO: mod_reports = Column(String)

class Comment(Base):
    __tablename__ = "comment"

    created_utc = Column(DateTime)
    id = Column(String, primary_key=True)
    redditor_name = Column(String, ForeignKey("redditor.name"))
    redditor = relationship("Redditor", back_populates="comments")
    body = Column(String)
    submission_id = Column(String, ForeignKey("submission.id"))
    submission = relationship("Submission", back_populates="comments")
    parent_id = Column(String)

# TODO: class RedditModLog(Base):