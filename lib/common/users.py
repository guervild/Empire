import threading
import string
import random
import hashlib
from . import helpers
import json
from pydispatch import dispatcher


class Users():
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

    def add_new_user(self, user_name, password):
        """
        Add new user to cache
        """
        last_logon = helpers.get_datetime()
        conn = self.get_db_connection()

        # MD5 hash password before storage
        password = hashlib.md5(password.encode('UTF-8'))
        md5_password = password.hexdigest()
        message = False

        try:
            self.lock.acquire()
            cur = conn.cursor()
            success = cur.execute("INSERT INTO users (username, password, last_logon_time, enabled, admin) VALUES (?,?,?,?,?)",
                        (user_name, md5_password, last_logon, True, False))

            if success:
                # dispatch the event
                signal = json.dumps({
                    'print': True,
                    'message': "Added {} to Users".format(user_name)
                })
                dispatcher.send(signal, sender="Users")
                message = True
            else:
                message = False

        finally:
            cur.close()
            self.lock.release()
            return message

    def disable_user(self, uid, disable):
        """
        Disable user
        """
        conn = self.get_db_connection()

        try:
            self.lock.acquire()
            cur = conn.cursor()
            admin = cur.execute("SELECT admin FROM users WHERE id = ? LIMIT 1", (uid,)).fetchone()

            if admin[0] == True:
                signal = json.dumps({
                    'print': True,
                    'message': "Cannot disable admin account"
                })
                message = False
            else:
                cur.execute("UPDATE users SET enabled = ? WHERE id = ?",
                            (not(disable), uid))
                signal = json.dumps({
                    'print': True,
                    'message': 'User {}'.format('disabled' if disable else 'enabled')
                })
                message = True
        finally:
            cur.close()
            self.lock.release()
            dispatcher.send(signal, sender="Users")
            return message

    def user_login(self, user_name, password):
        last_logon = helpers.get_datetime()
        conn = self.get_db_connection()

        # MD5 hash password before storage
        password = hashlib.md5(password.encode('UTF-8'))
        md5_password = password.hexdigest()
        try:
            self.lock.acquire()
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE username = ? AND password = ? AND enabled = true LIMIT 1"
                        , (user_name, md5_password))
            user = cur.fetchone()

            if user == None:
                return None

            token = self.refresh_api_token()
            cur.execute("UPDATE users SET last_logon_time = ?, api_token = ? WHERE username = ?",
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
            cur.execute("SELECT id, username, api_token, last_logon_time, enabled, admin FROM users WHERE api_token = ? LIMIT 1", (token,))
            [ id, username, api_token, last_logon_time, enabled, admin ] = cur.fetchone()

        finally:
            cur.close()
            self.lock.release()
            return { 'id': id, 'username': username, 'api_token': api_token, 'last_logon_time': last_logon_time, 'enabled': bool(enabled), 'admin': bool(admin) }

    def refresh_api_token(self):
        """
        Generates a randomized RESTful API token and updates the value
        in the config stored in the backend database.
        """
        # generate a randomized API token
        rng = random.SystemRandom()
        apiToken = ''.join(rng.choice(string.ascii_lowercase + string.digits) for x in range(40))

        return apiToken

    def update_password(self, uid, password):
        """
        Update the last logon timestamp for a user
        """
        # MD5 hash password before storage
        password = hashlib.md5(password.encode('UTF-8'))
        md5_password = password.hexdigest()
        print(md5_password)
        conn = self.get_db_connection()
        #TODO: add handling for updating password of non-existing users
        try:
            self.lock.acquire()
            cur = conn.cursor()

            cur.execute("UPDATE users SET password=? WHERE id=?", (md5_password, uid))

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
            cur.execute("UPDATE users SET api_token=null WHERE id=?", (uid,))

            # dispatch the event
            signal = json.dumps({
                'print': True,
                'message': "User disconnected"
            })
            dispatcher.send(signal, sender="Users")

        finally:
            cur.close()
            self.lock.release()

    def is_admin(self, uid):
        conn = self.get_db_connection()
        cur = conn.cursor()
        admin = cur.execute("SELECT admin FROM users WHERE id=?", (uid,)).fetchone()

        if admin[0] == True:
            return True

        return False
