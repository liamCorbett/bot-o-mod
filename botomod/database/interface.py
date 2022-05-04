from datetime import datetime
from typing import Union
import praw, prawcore
from sqlalchemy.orm import Session

from .crud import get_or_add, get_or_append
from .engine import db
from .models import Comment, Submission, Subreddit
from .models import Redditor, RedditorSnapshot

def get_or_add_redditor(session, redditor: praw.models.Redditor):
    try:
        return get_or_add(session, Redditor, redditor.name, 
            name=redditor.name, 
            created_utc=datetime.utcfromtimestamp(redditor.created_utc)
        )
    except (prawcore.exceptions.NotFound, AttributeError):
        return get_or_add(session, Redditor, "[missing]", 
            name="[missing]", 
            created_utc=None
        )

def save_submission_to_db(submission):

    subreddit = submission.subreddit
    
    with Session(db) as session, session.begin():
        db_subreddit = get_or_add(
            # Get
            session = session, 
            model = Subreddit, 
            key = subreddit.display_name, 
            # Add
            created_utc = datetime.utcfromtimestamp(subreddit.created_utc),
            display_name = subreddit.display_name,
            public_description = subreddit.public_description,
            subscribers = subreddit.subscribers,
            over18 = subreddit.over18
        )

        db_submission_redditor = get_or_add_redditor(
            session = session,
            redditor = submission.author
        )

        try: 
            db_redditor_snapshot = RedditorSnapshot(
                redditor = db_submission_redditor,
                name = submission.author.name,
                snapshot_utc = datetime.utcnow(),
                link_karma = submission.author.link_karma,
                comment_karma = submission.author.comment_karma,
                has_verified_email = submission.author.has_verified_email,
                subreddit_title = submission.author.subreddit.title,
                subreddit_description = submission.author.subreddit
                    .public_description,
                subreddit_nsfw = submission.author.subreddit.over_18
            )
            db_submission_redditor.redditor_snapshots.append(
                db_redditor_snapshot
            )
        except AttributeError:
            # We don't want a snapshot if the user has no info
            pass

        submission_properties = {
            'id': submission.id,
            'created_utc': datetime.utcfromtimestamp(submission.created_utc),
            'redditor': db_submission_redditor,
            'subreddit_display_name': subreddit.display_name,
            'subreddit': db_subreddit,
            'title': submission.title,
            'link_flair_text': submission.link_flair_text,
            'is_self': submission.is_self,
            'over_18': submission.over_18,
            'selftext': submission.selftext,
            'url': submission.url
        }
        try:
            submission_properties['redditor_name'] = submission.author.name
        except AttributeError:
            submission_properties['redditor_name'] = "[missing]"

        get_or_append(
            session = session,
            model = Submission,
            key = submission.id,
            append_to = [db_subreddit, db_submission_redditor],
            by_rel = "submissions",
            properties = submission_properties
        )

# Trying to maintain DRY between comments and submissions ended up
# ugly-ing the code something fierce. Better to just keep separate.
def save_comment_to_db(comment: praw.models.Comment):
    
    subreddit = comment.subreddit
    submission = comment.submission

    with Session(db) as session, session.begin():
        
        # Gets any subreddits from db that match the one containing our item
        # If it doesn't exist in the database, this creates it
        db_subreddit = get_or_add(
            # Get
            session = session, 
            model = Subreddit, 
            key = subreddit.display_name, 
            # Add
            created_utc = datetime.utcfromtimestamp(subreddit.created_utc),
            display_name = subreddit.display_name,
            public_description = subreddit.public_description,
            subscribers = subreddit.subscribers,
            over18 = subreddit.over18
        )

        db_submission_redditor = get_or_add_redditor(
            session = session,
            redditor = submission.author
        )

        db_comment_redditor = get_or_add_redditor(
            session = session,
            redditor = comment.author
        )

        try: 
            db_comment_redditor_snapshot = RedditorSnapshot(
                redditor = db_comment_redditor,
                name = comment.author.name,
                snapshot_utc = datetime.utcnow(),
                link_karma = comment.author.link_karma,
                comment_karma = comment.author.comment_karma,
                has_verified_email = comment.author.has_verified_email,
                subreddit_title = comment.author.subreddit.title,
                subreddit_description = comment.author.subreddit
                    .public_description,
                subreddit_nsfw = comment.author.subreddit.over_18
            )
            db_submission_redditor.redditor_snapshots.append(
                db_comment_redditor_snapshot
            )
        except AttributeError:
            # We don't want a snapshot if the user has no info
            pass

        submission_properties = {
            'id': submission.id,
            'created_utc': datetime.utcfromtimestamp(submission.created_utc),
            'redditor': db_submission_redditor,
            'subreddit_display_name': subreddit.display_name,
            'subreddit': db_subreddit,
            'title': submission.title,
            'link_flair_text': submission.link_flair_text,
            'is_self': submission.is_self,
            'over_18': submission.over_18,
            'selftext': submission.selftext,
            'url': submission.url
        }
        try:
            submission_properties['redditor_name'] = submission.author.name
        except AttributeError:
            submission_properties['redditor_name'] = "[missing]"

        db_submission = get_or_append(
            session = session,
            model = Submission,
            key = submission.id,
            append_to = [db_subreddit, db_submission_redditor],
            by_rel = "submissions",
            properties = submission_properties
        )

        comment_properties = {
            'created_utc': datetime.utcfromtimestamp(comment.created_utc),
            'id': comment.id,
            'redditor': db_comment_redditor,
            'body': comment.body,
            'submission_id': submission.id,
            'submission': db_submission,
            'parent_id': comment.parent_id
        }

        try:
            comment_properties['redditor_name'] = comment.author.name
        except AttributeError:
            comment_properties['redditor_name'] = "[missing]"

        get_or_append(
            session = session,
            model = Comment,
            key = comment.id,
            append_to = [db_submission, db_comment_redditor],
            by_rel = "comments",
            properties = comment_properties
        )
    
def save_to_db(item: Union[praw.models.Comment, praw.models.Submission]):
    """Saves item to database.

    Args:
        item: the praw submission or praw comment to save to the database
    """

    if isinstance(item, praw.models.Comment):
        return save_comment_to_db(item)
    elif isinstance(item, praw.models.Submission):
        return save_submission_to_db(item)
    else:
        raise TypeError("Item isn't of type Comment or Submission")
            