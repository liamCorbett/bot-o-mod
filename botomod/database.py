import yaml
from sqlalchemy import create_engine, engine
from sqlalchemy import Column, ForeignKey
from sqlalchemy.types import Integer, String, DateTime, Boolean
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy_utils import database_exists


with open("config.yaml") as config_file:
    config = yaml.safe_load(config_file)
    db_user = config["db_user"]
    db_pass = config["db_pass"]
    db_hostname = config["db_hostname"]
    db_port = config["db_port"]
    db_name = config["db_name"]
    db_adminpass = config["db_adminpass"]

Base = declarative_base()

def init_connection_engine():
    db_config = {
        "echo": True,
        "future": True
    }

    # Equivalent URL:
    # postgresql+psycopg2://<db_user>:<db_pass>@<db_host>:<db_port>/<db_name>
    db_url = engine.url.URL.create(
            drivername="postgresql+psycopg2",
            username=db_user,  # e.g. "my-database-user"
            password=db_pass,  # e.g. "my-database-password"
            host=db_hostname,  # e.g. "127.0.0.1"
            port=db_port,      # e.g. 5432
            database=db_name   # e.g. "my-database-name"
        )

    if not database_exists(db_url):
        temp_engine = create_engine(f"postgresql+psycopg2://postgres:{db_adminpass}@localhost:5432/postgres")
        with temp_engine.connect() as conn:
            conn.execute("commit")
            # Do not substitute user-supplied database names here.
            conn.execute(
                f"CREATE DATABASE {db_name};"
            )
            conn.execute(
                f"CREATE USER {db_user} WITH PASSWORD '{db_pass}';"
                f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user}"
            )

    db = create_engine(db_url, **db_config)

    return db

def create_tables(db):
    # Create tables (if they don't already exist)
    Base.metadata.create_all(db, checkfirst=True)

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