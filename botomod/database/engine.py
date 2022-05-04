import datetime, logging, os
import yaml
from sqlalchemy import create_engine, engine
from sqlalchemy_utils import database_exists
from .models import Base

engine_filename = os.path.join(
    "./logs/sqlalchemy/", 
    "{0}-engine.log".format(datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
)
engine_fh = logging.FileHandler(engine_filename, encoding='utf-8')
engine_fh.setLevel(logging.DEBUG)

engine_logger = logging.getLogger("sqlalchemy.engine")
engine_logger.setLevel(logging.INFO)
engine_logger.propagate = False
engine_logger.addHandler(engine_fh)

pool_filename = os.path.join(
    "./logs/sqlalchemy/", 
    "{0}-pool.log".format(datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
)
pool_fh = logging.FileHandler(pool_filename, encoding='utf-8')
pool_fh.setLevel(logging.DEBUG)

pool_logger = logging.getLogger("sqlalchemy.pool")
pool_logger.setLevel(logging.DEBUG)
pool_logger.propagate = False
pool_logger.addHandler(pool_fh)

# TODO: Better way of pulling config into this module
with open("config.yaml") as config_file:
    config = yaml.safe_load(config_file)
    db_adminpass = config["db_adminpass"]
    db_user = config["db_user"]
    db_pass = config["db_pass"]
    db_hostname = config["db_hostname"]
    db_port = config["db_port"]
    db_name = config["db_name"]

def create_database():
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

def init_connection_engine():
    db_config = {"echo": False, "future": True}
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
        create_database()
    db = create_engine(db_url, **db_config)
    # Create tables if they don't already exist
    Base.metadata.create_all(db, checkfirst=True)
    return db

db = init_connection_engine()