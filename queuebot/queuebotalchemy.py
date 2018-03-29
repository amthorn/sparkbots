from config import MYSQL_CONFIG

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from app import app

# Build sql engine
engine = create_engine(
    'mysql+mysqldb://{}@{}/{}'.format(
        MYSQL_CONFIG['MYSQL_USER'],
        MYSQL_CONFIG['MYSQL_HOST'],
        MYSQL_CONFIG['MYSQL_DB']
    )
)
Base = declarative_base()

Base.metadata.bind = engine

from queuebot import models  # noqa

class QueueBotAlchemy:
    def __init__(self):
        # SQL Session
        DBSession = sessionmaker()
        DBSession.bind = engine
        app.session = DBSession()

    def purge_tables():
        # delete databases
        Base.metadata.drop_all(engine)

        # create the databases again
        Base.metadata.create_all(engine)
        app.session.commit()