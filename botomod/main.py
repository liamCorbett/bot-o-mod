from datetime import datetime
from types import SimpleNamespace
from typing import Union
import praw, prawcore, yaml
from sqlalchemy.orm import Session
from database import init_connection_engine
from models import Subreddit, RedditSubmission, RedditComment
from models import RedditUser, RedditUserSnapshot

with open("config.yaml") as config_file:
    config = yaml.safe_load(config_file)

    # Communities to stream comments and submissions from
    watched_subreddits = config["watched_subreddits"]

    # Users to omit from scans (only maintains enough info for bot operation)
    do_not_scan_users = config["do_not_scan_users"]

    # User activity in these subreddits prompt action from the bot
    report_subs = config["report_subs"] # Report 
    filter_subs = config["filter_subs"] # Report AND remove
    remove_subs = config["remove_subs"] # Remove only; no report (try 2 avoid)

    # User descriptions which match the following text prompt action from bot
    report_desc = config["report_desc"]
    filter_desc = config["filter_desc"]
    remove_desc = config["remove_desc"]

# See https://praw.readthedocs.io/en/stable/getting_started/configuration/prawini.html
reddit = praw.Reddit("MeetBot")

def get_or_add(session, model, key, **properties):
    instance = session.query(model).get(key)
    if instance:
        return instance
    else:
        instance = model(**properties)
        session.add(instance)
        return instance

# TODO: this probably isn't very elegant
def get_or_add_reddit_user(session, redditor):
    """Gets or adds a new user to the database; handles missing users

    Args:
        session: The SQLAlchemy database session
        redditor:

    Returns:
        An instance of RedditUser
    """
    try:
        return get_or_add(session, RedditUser, redditor.name, 
            reddit_username=redditor.name, 
            created_utc=datetime.utcfromtimestamp(redditor.created_utc)
        )
    except (prawcore.exceptions.NotFound, AttributeError):
        return get_or_add(session, RedditUser, "[missing]", 
            reddit_username="[missing]", 
            created_utc=None
        )

def get_or_append(*, session, model, key, properties, append_to, by_rel):
    """Gets instance of model; or creates and appends a new one if none found

    Args:
        session: the SQLAlchemy database session
        model: the model to search in, or instantiate
        key: the primary key to search for
        properties: a dict of properties to instantiate 
        append_to: a list of parent instances to add new child to
        rel: 

    Returns:
        An instance of child_model
    """
    instance = session.query(model).get(key)
    if instance:
        return instance
    else:
        instance = model(**properties)
        for parent in append_to:
            getattr(parent, by_rel).append(instance)
        return instance


def save_to_db(item: Union[praw.models.Comment, praw.models.Submission]):
    """Saves item to database.

    Args:
        item: the praw submission or praw comment to save to the database
    """

    # WARNING: PRAW objects are lazy
    author = item.author              # PRAW Redditor object
    subreddit = item.subreddit        # PRAW Subreddit object

    if isinstance(item, praw.models.Comment):
        type = "comment"
        submission = item.submission
        comment = item
    elif isinstance(item, praw.models.Submission):
        type = "submission"
        submission = item
    else:
        raise TypeError("Item isn't of type Comment or Submission")

    with Session(db) as session, session.begin():

        # Gets any subreddits from db that match the one containing our item
        # If it doesn't exist in the database, this creates it
        reddit_subreddit = get_or_add(
            # Get
            session = session, 
            model = Subreddit, 
            key = subreddit.display_name, 
            # Add
            created_utc = datetime.utcfromtimestamp(subreddit.created_utc),
            name = subreddit.name,
            display_name = subreddit.display_name,
            id = subreddit.id,
            description = subreddit.description,
            public_description = subreddit.public_description,
            subscribers = subreddit.subscribers,
            over18 = subreddit.over18
        )

        # Same logic as above but for author of item
        reddit_user = get_or_add_reddit_user(
            session = session, 
            redditor = author
        )

        # No need for get_or_add since we basically always want to create a
        # snapshot, unless the user is deleted / suspended and has no data.
        try:
            reddit_user_snapshot = RedditUserSnapshot(
                reddit_user = reddit_user,
                reddit_username = author.name,
                snapshot_utc = datetime.utcnow(),
                link_karma = author.link_karma,
                comment_karma = author.comment_karma,
                has_verified_email = author.has_verified_email,
                subreddit_title = author.subreddit.title,
                subreddit_description = author.subreddit.public_description,
                subreddit_nsfw = author.subreddit.over_18
            )
            reddit_user.reddit_user_snapshots.append(reddit_user_snapshot)
        except AttributeError:
            pass

        # If present: adds parent submission's user to database
        if type == "comment":
            submission_user = get_or_add_reddit_user(
                session = session,
                redditor = submission.author
            )

        submission_properties = {
            'id': submission.id,
            'reddit_username': submission.author.name,
            'reddit_user': reddit_user if type == "submission" 
                else submission_user,
            'subreddit_display_name': subreddit.display_name,
            'subreddit': reddit_subreddit,
            'title': submission.title,
            'selftext': submission.selftext,
            'permalink': submission.permalink,
            'url': submission.url,
            'link_flair_text': submission.link_flair_text,
            'is_self': submission.is_self,
            'over_18': submission.over_18
        }

        reddit_submission = get_or_append(
            session = session,       
            model = RedditSubmission, 
            key = submission.id,
            append_to = [reddit_subreddit, reddit_user],
            by_rel = 'reddit_submissions',
            properties = submission_properties
        )

        if type == "comment":
            get_or_append(
                session = session,
                model = RedditComment,
                key = comment.id,
                append_to = [reddit_submission],
                by_rel = 'reddit_comments',
                properties = {
                    'created_utc': datetime.utcfromtimestamp(
                        comment.created_utc
                    ),
                    'id': comment.id,
                    'body': comment.body,
                    'reddit_username': author.name,
                    'reddit_user': reddit_user,
                    'reddit_submission_id': submission.id,
                    'reddit_submission': reddit_submission,
                    'permalink': comment.permalink,
                    'parent_id': comment.parent_id
                }
            )
            


def process_submissions(submissions, save=True):
    for submission in submissions:
        if submission is None:
            break

        print("POST: ", submission.title)

        if save:
            save_to_db(submission)

def process_comments(comments, save=True):
    for comment in comments:
        if comment is None:
            break

        print("COMMENT: ", comment.body)

        if save:
            save_to_db(comment)

def main():
    submissions = get_stream().submissions(
        pause_after=-1, 
        skip_existing=True
    )
    comments = get_stream().comments(
        pause_after=-1, 
        skip_existing=True
    )

    while True:
        process_submissions(submissions)
        process_comments(comments)

def get_stream():
    """
    
    Returns:
        praw.reddit.Subreddit.stream: The stream of all watched subreddits
    """
    return reddit.subreddit("+".join(watched_subreddits)).stream

if __name__ == "__main__":
    global db # sqlalchemy database
    db = init_connection_engine()
    main()