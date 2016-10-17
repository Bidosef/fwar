# coding: utf-8 
import os
import psycopg2
import urlparse

urlparse.uses_netloc.append("postgres")
url = urlparse.urlparse(os.environ["DATABASE_URL"])



def openDB():
    return psycopg2.connect(
        database=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port
    )

db = openDB()
query = db.cursor()

query.execute('CREATE TABLE Players (ID SERIAL PRIMARY KEY, Pseudo TEXT, Password TEXT,  Type INT, Score INT) ')

query.close()
db.close()

