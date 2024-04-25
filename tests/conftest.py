# Common pytest fixtures

import os
from pymongo import MongoClient
import pytest
import secrets


@pytest.fixture( autouse=True, scope='session' )
def mongo_db():
    '''Return a session-wide mongodb database connection'''

    # Connect with the provided connect string or localhost
    client = MongoClient( os.environ.get('MONGO_CONNECT_URI') or 'mongodb://127.0.0.1:27017' )
    dbname = secrets.token_hex(6)
    yield client[ dbname ]

    # Clean up
    client.drop_database( dbname )
    client.close()
