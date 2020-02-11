import sys
import base64
import sqlite3
import datetime
import threading
import string
import random
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


    def add_new_user(self, user_Name, password):
        """
        Add new user to cache
        """
        last_logon = helpers.get_datetime()
        conn = self.get_db_connection()

        try:
            self.lock.acquire()
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM users WHERE username = ? LIMIT 1", (user_Name,))
            found = cur.fetchone()
            if not found:
                cur.execute("INSERT INTO users (username, password, last_logon_time) VALUES (?,?,?)",
                            (user_Name, password, last_logon))
            #TODO: Add token generation for new user


            #TODO: extract update to its own function
            else:
                cur.execute("UPDATE users SET last_logon_time = ? WHERE username = ?",
                            (last_logon, user_Name))
        finally:
            cur.close()
            self.lock.release()
            # dispatch the event
            signal = json.dumps({
                'print': True,
                'message': "{} connected".format(user_Name)
            })
            dispatcher.send(signal, sender="Users")


    def user_login(self, user_name, password):
        last_logon = helpers.get_datetime()
        conn = self.get_db_connection()

        try:
            self.lock.acquire()
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM users WHERE username = ? AND password = ? LIMIT 1", (user_name, password))
            found = cur.fetchone()
            if not found:
                return None
            # TODO: extract update to its own function
            else:
                token = self.refresh_api_token()
                cur.execute("UPDATE users SET last_logon_time = ?, api_current_token = ? WHERE username = ?",
                            (last_logon, token, user_name))
                # dispatch the event
                signal = json.dumps({
                    'print': True,
                    'message': "{} connected".format(user_name)
                })
                dispatcher.send(signal, sender="Users")
                return token
        finally:
            cur.close()
            self.lock.release()


    def get_user_from_token(self, token):
        conn = self.get_db_connection()

        try:
            self.lock.acquire()
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE api_current_token = ? LIMIT 1", (token,))
            found = cur.fetchone()
            return found

        finally:
            cur.close()
            self.lock.release()


    def refresh_api_token(self):
        """
        Generates a randomized RESTful API token and updates the value
        in the config stored in the backend database.
        """
        # generate a randomized API token
        rng = random.SystemRandom()
        apiToken = ''.join(rng.choice(string.ascii_lowercase + string.digits) for x in range(40))

        return apiToken