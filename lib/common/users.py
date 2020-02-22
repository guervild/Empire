import threading
import string
import random
import hashlib
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
        enabled = 1

        # MD5 hash password before storage
        password = hashlib.md5(password.encode('UTF-8'))
        md5_password = password.hexdigest()

        try:
            self.lock.acquire()
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM users WHERE username = ? LIMIT 1", (user_Name,))
            found = cur.fetchone()
            if not found:
                uid = ''.join(random.choice(string.ascii_lowercase + string.digits) for x in range(40))
                cur.execute("INSERT INTO users (username, password, last_logon_time, unique_id,enabled) VALUES (?,?,?,?,?)",
                            (user_Name, md5_password, last_logon,uid,enabled))

                # dispatch the event
                signal = json.dumps({
                    'print': True,
                    'message': "Added {} to Users".format(user_Name)
                })
                dispatcher.send(signal, sender="Users")
                message = True
            else:
                message = False

        finally:
            cur.close()
            self.lock.release()
            return message

    def disable_user(self, uid):
        """
        Delete user from cache
        """
        conn = self.get_db_connection()
        enabled = 0

        try:
            self.lock.acquire()
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM users WHERE unique_id = ? AND id = '1' LIMIT 1", (uid,))
            found = cur.fetchone()
            if found:
                signal = json.dumps({
                    'print': True,
                    'message': "Cannot disable admin account"
                })
                message = False
            else:
                cur.execute("SELECT 1 FROM users WHERE unique_id = ? AND enabled = '1'", (uid,))
                found = cur.fetchone()
                if found:
                    cur.execute("UPDATE users SET enabled = ? WHERE unique_id = ? AND id != '1'",
                                (enabled, uid))
                    signal = json.dumps({
                        'print': True,
                        'message': "User Disabled"
                    })
                    message = True
                else:
                    signal = json.dumps({
                        'print': True,
                        'message': "User already disabled"
                    })
                    message = False
        finally:
            cur.close()
            self.lock.release()
            dispatcher.send(signal, sender="Users")
            return message


    def enable_user(self, user_name):
        """
        Enable user from cache
        """
        conn = self.get_db_connection()
        enabled = 1

        try:
            self.lock.acquire()
            cur = conn.cursor()
            cur.execute("UPDATE users SET enabled = ? WHERE username = ?",
                        (enabled, user_name))
            # dispatch the event
            signal = json.dumps({
                'print': True,
                'message': "Enabled {} from Users".format(user_name)
            })
            dispatcher.send(signal, sender="Users")

        finally:
            cur.close()
            self.lock.release()


    def user_login(self, user_name, password):
        last_logon = helpers.get_datetime()
        conn = self.get_db_connection()

        # MD5 hash password before storage
        password = hashlib.md5(password.encode('UTF-8'))
        md5_password = password.hexdigest()

        try:
            self.lock.acquire()
            cur = conn.cursor()
            cur.execute("SELECT enabled FROM users WHERE username = ? AND password = ? LIMIT 1"
                        , (user_name, md5_password))
            enabled = cur.fetchone()
            enabled = int(''.join(map(str, enabled)))

            if enabled == 1:
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
            else:
                return None
        finally:
            cur.close()
            self.lock.release()

    def get_user_from_token(self, token):
        conn = self.get_db_connection()

        try:
            self.lock.acquire()
            cur = conn.cursor()
            cur.execute("SELECT username FROM users WHERE api_current_token = ? LIMIT 1", (token,))
            username = cur.fetchone()

        finally:
            cur.close()
            self.lock.release()
            return username[0]


    def get_uid_from_token(self, token):
        conn = self.get_db_connection()

        try:
            self.lock.acquire()
            cur = conn.cursor()
            cur.execute("SELECT unique_id FROM users WHERE api_current_token = ? LIMIT 1", (token,))
            uid = cur.fetchone()

        finally:
            cur.close()
            self.lock.release()
            return uid[0]


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

    def update_password(self, uid, password):
        """
        Update the last logon timestamp for a user
        """
        # MD5 hash password before storage
        password = hashlib.md5(password.encode('UTF-8'))
        md5_password = password.hexdigest()

        conn = self.get_db_connection()
        #TODO: add handling for updating password of non-existing users
        try:
            self.lock.acquire()
            cur = conn.cursor()

            cur.execute("UPDATE users SET password=? WHERE unique_id=?", (md5_password, uid))

            # dispatch the event
            signal = json.dumps({
                'print': True,
                'message': "Password updated"
            })
            dispatcher.send(signal, sender="Users")

        finally:
            cur.close()
            self.lock.release()
            return True


    def user_logout(self, uid):
        conn = self.get_db_connection()

        try:
            self.lock.acquire()
            cur = conn.cursor()
            cur.execute("UPDATE users SET api_current_token=null WHERE unique_id=?", (uid,))

            # dispatch the event
            signal = json.dumps({
                'print': True,
                'message': "User disconnected"
            })
            dispatcher.send(signal, sender="Users")

        finally:
            cur.close()
            self.lock.release()