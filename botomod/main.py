import praw, yaml
from database import save_to_db

with open("config.yaml") as config_file:
    config = yaml.safe_load(config_file)

    # Communities to stream comments and submissions from
    cfg_watched_subreddits = config["watched_subreddits"]

    # Users to omit from scans (only maintains enough info for bot operation)
    cfg_do_not_scan_users = config["do_not_scan_users"]

    # User activity in these subreddits prompt action from the bot
    cfg_report_subs = config["report_subs"] # Report 
    cfg_filter_subs = config["filter_subs"] # Report AND remove
    cfg_remove_subs = config["remove_subs"] # Remove only; no report (try 2 avoid)

    # User descriptions which match the following text prompt action from bot
    cfg_report_desc = config["report_desc"]
    cfg_filter_desc = config["filter_desc"]
    cfg_remove_desc = config["remove_desc"]

# See https://praw.readthedocs.io/en/stable/getting_started/configuration/prawini.html
reddit = praw.Reddit("MeetBot")

def process_submissions(submissions, save=True):
    for submission in submissions:
        if submission is None:
            break

        print("\n\nPOST: ", submission.title, "\n\n")

        if save:
            save_to_db(submission)

def process_comments(comments, save=True):
    for comment in comments:
        if comment is None:
            break

        print("\n\nCOMMENT: ", comment.body, "\n\n")

        if save:
            save_to_db(comment)

def get_stream(watched_subreddits):
    """Gets a stream of watched subreddits
    
    Returns:
        praw.reddit.Subreddit.stream: The stream of all watched subreddits
    """
    return reddit.subreddit("+".join(watched_subreddits)).stream

def main_loop():
    submissions = get_stream(cfg_watched_subreddits).submissions(
        pause_after=-1, 
        skip_existing=True
    )
    comments = get_stream(cfg_watched_subreddits).comments(
        pause_after=-1, 
        skip_existing=True
    )

    while True:
        process_submissions(submissions)
        process_comments(comments)

if __name__ == "__main__":
    main_loop()