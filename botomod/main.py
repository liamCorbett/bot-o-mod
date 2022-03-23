from datetime import datetime
from types import SimpleNamespace
from typing import Union
import praw, yaml
from prawcore.exceptions import NotFound
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

def save_to_db(
    item: Union[praw.Reddit.comment, praw.Reddit.submission], 
    type: str):
    """Saves item to database.

    Args:
        item: the praw submission or praw comment to save to the database
        type: "submission" or "comment", depending on the item being passed
    """

    with Session(db) as session, session.begin():
        try:
            author = item.author
            author.name
        except AttributeError:
            author = SimpleNamespace(name="[deleted]")

        subreddit = item.subreddit

        # Gets any subreddits from db that match the one containing our item
        # If it doesn't exist in the database, this creates it
        reddit_subreddit = session.query(Subreddit).get(subreddit.display_name)
        if not reddit_subreddit:
            reddit_subreddit = Subreddit(
                created_utc = datetime.utcfromtimestamp(subreddit.created_utc),
                name = subreddit.name,
                display_name = subreddit.display_name,
                id = subreddit.id,
                description = subreddit.description,
                public_description = subreddit.public_description,
                subscribers = subreddit.subscribers,
                over18 = subreddit.over18
            )
            session.add(reddit_subreddit)

        # Same logic as above but for author of item
        reddit_user = session.query(RedditUser).get(author.name)
        if not reddit_user:
            try:
                reddit_user = RedditUser(
                    reddit_username = author.name,
                    created_utc = datetime.utcfromtimestamp(
                        author.created_utc
                    )
                )
            except NotFound:
                reddit_user = RedditUser(
                    reddit_username = author.name,
                    created_utc = None
                )
            session.add(reddit_user)

        # We don't conditionally create user snapshots since we pretty much 
        # always want a new one, unless the user is suspended
        # (in which case praw will raise NotFound)
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
        except NotFound:
            reddit_user_snapshot = None

        # If the item is a comment, then our "submission" refers to the
        # post that the comment belongs to. 
        if type == "submission":
            submission = item
            submission_user = reddit_user
        elif type == "comment":
            comment = item
            submission = comment.submission
            submission_user = session.query(RedditUser).get(
                submission.author.name
            )
            if not submission_user:
                try: 
                    submission_user = RedditUser(
                        reddit_username = submission.author.name,
                        created_utc = datetime.utcfromtimestamp(
                            submission.author.created_utc
                        )
                    )
                except NotFound:
                    submission_user = RedditUser(
                        reddit_username = submission.author.name,
                        created_utc = None
                    )
                session.add(submission_user)

        reddit_submission = session.query(RedditSubmission).get(submission.id)
        if not reddit_submission:
            reddit_submission = RedditSubmission(
                id = submission.id,
                created_utc = datetime.utcfromtimestamp(
                    submission.created_utc
                ),
                reddit_username = author.name,
                reddit_user = submission_user,
                subreddit_display_name = subreddit.display_name,
                subreddit = reddit_subreddit,
                title = submission.title,
                selftext = submission.selftext,
                permalink = submission.permalink,
                url = submission.url,
                link_flair_text = submission.link_flair_text,
                is_self = submission.is_self,
                over_18 = submission.over_18
            )

        if type == "comment":
            reddit_comment = session.query(RedditComment).get(comment.id)
            if not reddit_comment:
                reddit_comment = RedditComment(
                    created_utc = datetime.utcfromtimestamp(
                        comment.created_utc
                    ),
                    id = comment.id,
                    body = comment.body,
                    reddit_username = author.name,
                    reddit_user = reddit_user,
                    reddit_submission_id = submission.id,
                    reddit_submission = reddit_submission,
                    permalink = comment.permalink,
                    parent_id = comment.parent_id
                )

        # Add everything to DB
        if reddit_user_snapshot:
            reddit_user.reddit_user_snapshots.append(reddit_user_snapshot)

        submission_user.reddit_submissions.append(reddit_submission)
        reddit_subreddit.reddit_submissions.append(reddit_submission)

        if type == "comment":
            reddit_user.reddit_comments.append(reddit_comment)


def process_submissions(submissions, save=True):
    for submission in submissions:
        if submission is None:
            break

        print("POST: ", submission.title)

        if save:
            save_to_db(submission, "submission")

def process_comments(comments, save=True):
    for comment in comments:
        if comment is None:
            break

        print("COMMENT: ", comment.body)

        if save:
            save_to_db(comment, "comment")

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