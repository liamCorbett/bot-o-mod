from datetime import datetime
import praw, yaml
from sqlalchemy.orm import Session
from database import init_connection_engine, create_tables
from database import Subreddit, RedditSubmission, RedditComment
from database import RedditUser, RedditUserSnapshot


with open("config.yaml") as config_file:
    config = yaml.safe_load(config_file)
    client_id = config["client_id"]
    client_secret = config["client_secret"]
    username = config["username"]
    password = config["password"]
    user_agent = config["user_agent"]
    mod_sub = config["mod_sub"]
    banned_subs = config["banned_subs"]
    suspicious_subs = config["suspicious_subs"]
    banned_user_descriptions = config["banned_user_descriptions"]
    removal_message = config["removal_message"]
    watched_communities = config["watched_communities"]
    database_engine = config["database_engine"]

# See https://praw.readthedocs.io/en/stable/getting_started/configuration/prawini.html#praw-ini
reddit = praw.Reddit("MeetBot")

def save_to_db(item, type):
    """Saves item to database.

    Args:
        item: the praw submission or praw comment to save to the database
        type: "submission" or "comment", depending on the item being passed
    """

    with Session(db) as session, session.begin():
        author = item.author
        subreddit = item.subreddit

        # Variables for passing to database session

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

        reddit_user = session.query(RedditUser).get(author.name)
        if not reddit_user:
            reddit_user = RedditUser(
                reddit_username = author.name,
                created_utc = datetime.utcfromtimestamp(author.created_utc)
            )
            session.add(reddit_user)

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

        if type == "submission":
            submission = item
            submission_user = reddit_user
        elif type == "comment":
            comment = item
            submission = comment.submission
            submission_user = session.query(RedditUser).get(submission.author.name)
            if not submission_user:
                submission_user = RedditUser(
                    reddit_username = submission.author.name,
                    created_utc = datetime.utcfromtimestamp(
                        submission.author.created_utc
                    )
                )
                session.add(submission_user)

        reddit_submission = session.query(RedditSubmission).get(submission.id)
        if not reddit_submission:
            reddit_submission = RedditSubmission(
                id = submission.id,
                created_utc = datetime.utcfromtimestamp(submission.created_utc),
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
                    created_utc = datetime.utcfromtimestamp(comment.created_utc),
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
    return reddit.subreddit("+".join(watched_communities)).stream

if __name__ == "__main__":
    global db # sqlalchemy database
    db = init_connection_engine()
    create_tables(db) # creates if none exist*
    main()