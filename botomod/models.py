from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.types import Boolean, DateTime, Integer, String

Base = declarative_base()


#   Subreddit           RedditUser
#        \              /        \
#         \            /          \
#        RedditSubmission     RedditUserSnapshot
#               |
#               |
#         RedditComment

class Subreddit(Base):
    __tablename__ = "subreddit"

    created_utc = Column(DateTime)
    name = Column(String)
    display_name = Column(String, primary_key=True)
    id = Column(String)
    description = Column(String)
    public_description = Column(String)
    subscribers = Column(Integer)
    over18 = Column(Boolean)
    reddit_submissions = relationship("RedditSubmission", back_populates="subreddit")

class RedditUser(Base):
    __tablename__ = "reddit_user"

    reddit_username = Column(String, primary_key=True)
    created_utc = Column(DateTime)
    reddit_user_snapshots = relationship(
        "RedditUserSnapshot", back_populates="reddit_user"
    )
    reddit_submissions = relationship(
        "RedditSubmission", back_populates="reddit_user"
    )
    reddit_comments = relationship(
        "RedditComment", back_populates="reddit_user"
    )

class RedditUserSnapshot(Base):
    __tablename__ = "reddit_user_snapshot"

    reddit_user = relationship("RedditUser", back_populates="reddit_user_snapshots")
    reddit_username = Column(String, ForeignKey("reddit_user.reddit_username"), primary_key=True)
    snapshot_utc = Column(DateTime, primary_key=True)
    link_karma = Column(Integer)
    comment_karma = Column(Integer)
    has_verified_email = Column(Boolean)
    subreddit_title = Column(String)
    subreddit_description = Column(String)
    subreddit_nsfw = Column(String)
    # TODO: estimated_age = Column(Integer)
    # TODO: estimated_gender = Column(String)

class RedditSubmission(Base):
    __tablename__ = "reddit_submission"

    id = Column(String, primary_key=True)
    created_utc = Column(DateTime)
    reddit_username = Column(String, ForeignKey("reddit_user.reddit_username"))
    reddit_user = relationship("RedditUser", back_populates="reddit_submissions")
    subreddit_display_name = Column(String, ForeignKey("subreddit.display_name"))
    subreddit = relationship("Subreddit", back_populates="reddit_submissions")
    reddit_comments = relationship("RedditComment", back_populates="reddit_submission")
    title = Column(String)
    selftext = Column(String)
    permalink = Column(String)
    url = Column(String)
    link_flair_text = Column(String)
    is_self = Column(Boolean)
    over_18 = Column(Boolean)
    # TODO: user_reports = Column(String)
    # TODO: mod_reports = Column(String)

class RedditComment(Base):
    __tablename__ = "reddit_comment"

    created_utc = Column(DateTime)
    id = Column(String, primary_key=True)
    body = Column(String)
    reddit_username = Column(String, ForeignKey("reddit_user.reddit_username"))
    reddit_user = relationship("RedditUser", back_populates="reddit_comments")
    reddit_submission_id = Column(String, ForeignKey("reddit_submission.id"))
    reddit_submission = relationship("RedditSubmission", back_populates="reddit_comments")
    permalink = Column(String)
    parent_id = Column(String)

# TODO: class RedditModLog(Base):