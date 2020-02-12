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

                # dispatch the event
                signal = json.dumps({
                    'print': True,
                    'message': "Added {} to Users".format(user_Name)
                })
                dispatcher.send(signal, sender="Users")

        finally:
            cur.close()
            self.lock.release()

    def delete_user(self, user_name):
        """
        Delete user from cache
        """
        conn = self.get_db_connection()

        try:
            self.lock.acquire()
            cur = conn.cursor()
            cur.execute("DELETE FROM users WHERE username = ? LIMIT 1", (user_name,))

            # dispatch the event
            signal = json.dumps({
                'print': True,
                'message': "Deleted {} from Users".format(user_name)
            })
            dispatcher.send(signal, sender="Users")

        finally:
            cur.close()
            self.lock.release()


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


    def update_last_logon(self, token):
        """
        Update the last logon timestamp for a user
        """
        last_logon = helpers.get_datetime()
        conn = self.get_db_connection()

        try:
            self.lock.acquire()
            cur = conn.cursor()

            cur.execute("UPDATE users SET last_logon_time=? WHERE api_current_token=?", (last_logon, token))

        finally:
            cur.close()
            self.lock.release()

    def update_password(self, user_name, password):
        """
        Update the last logon timestamp for a user
        """
        conn = self.get_db_connection()

        try:
            self.lock.acquire()
            cur = conn.cursor()

            cur.execute("UPDATE users SET password=? WHERE username=?", (password, user_name))

            # dispatch the event
            signal = json.dumps({
                'print': True,
                'message': "Updated password for {}".format(user_name)
            })
            dispatcher.send(signal, sender="Users")

        finally:
            cur.close()
            self.lock.release()
