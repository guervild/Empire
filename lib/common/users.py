import sys
import base64
import sqlite3
import datetime
import threading
from . import helpers
import json
from pydispatch import dispatcher

class Users():
    # This is a demo class for handling users
    # usercache represents the db
    def __init__(self, mainMenu):
        self.mainMenu = mainMenu

        self.conn = self.mainMenu.conn

        self.lock = threading.Lock()

        self.args = self.mainMenu.args

        self.users = {}

    def get_db_connection(self):
        """
        Returns a handle to the DB
        """
        self.lock.acquire()
        self.mainMenu.conn.row_factory = None
        self.lock.release()
        return self.mainMenu.conn

    def add_new_user(self, user_Name):
        """
        Add new user to cache
        """
        lastlogon = helpers.get_datetime()
        conn = self.get_db_connection()

        try:
            self.lock.acquire()
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM users WHERE username = ? LIMIT 1", (user_Name,))
            found = cur.fetchone()
            if not found:
                cur.execute("INSERT INTO users (username, lastlogon_time) VALUES (?,?)",
                            (user_Name, lastlogon))
            else:
                cur.execute("UPDATE users SET lastlogon_time = ? WHERE username = ?",
                            (lastlogon, user_Name))
        finally:
            cur.close()
            self.lock.release()
            # dispatch the event
            signal = json.dumps({
                'print': True,
                'message': "{} connected".format(user_Name)
            })
            dispatcher.send(signal, sender="Users")