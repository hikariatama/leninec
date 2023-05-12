import contextlib
import hashlib
import json
import os
import random
import re
import sqlite3
import string
import time
import typing
from pathlib import Path

try:
    import jwt
except ImportError:
    import python_jwt as jwt

from models import User, UserCredentials

DB_PATH = (
    Path("/data/users.sqlite")
    if os.environ.get("LENINEC_DOCKER")
    else Path(__file__).parent.joinpath("users.sqlite")
)

secrets = Path(__file__).parent.joinpath("secrets.json")

try:
    with secrets.open() as f:
        secrets = json.load(f)
        SECRET = secrets["jwt"]
        SALT = secrets["salt"]
except FileNotFoundError:
    SECRET, SALT = ("".join(random.choice(string.printable) for _ in range(30)) for _ in range(2))
    with secrets.open("w") as f:
        json.dump(
            {"jwt": SECRET, "salt": SALT},
            f,
        )


class _SQliteContextManager:
    def __init__(self, db_path: Path):
        self._db_path = db_path

    def __enter__(self):
        self.conn = sqlite3.connect(self._db_path)
        return self.conn.cursor()

    def __exit__(self, *_):
        self.conn.commit()
        self.conn.close()


class Database:
    def __init__(self):
        self.db = _SQliteContextManager(DB_PATH)
        self._salt = "'+zA+'s#^@0C:+z(cfx8-?-eoZ56K"

        with contextlib.suppress(sqlite3.OperationalError), self.db as cursor:
            cursor.execute(
                """
                CREATE TABLE users (
                    username TEXT,
                    password TEXT,
                    fullname TEXT,
                    teachercode TEXT,
                    role TEXT,
                    task TEXT,
                    usergroup TEXT,
                    taskstatus TEXT,
                    taskvars INT,
                    PRIMARY KEY (username)
                )
                """
            )

        with contextlib.suppress(sqlite3.OperationalError), self.db as cursor:
            cursor.execute("ALTER TABLE users ADD COLUMN taskvars INT")
            cursor.execute("UPDATE users SET taskvars = 1")

    def embed_salt(self, password: str) -> str:
        """
        Embeds the salt into the password using non-standart way.
        :param password: password to embed salt into
        :return: password with salt embedded
        """
        return "".join(a + b for a, b in zip(password, self._salt)) + self._salt

    def register(self, user: User) -> bool:
        """
        Adds user to the database.
        :param user: user to add
        :return: True if user was added, False if user already exists
        """
        if len(user.username) not in range(3, 32) or len(user.password) not in range(
            6, 64
        ):
            return False

        with self.db as cursor:
            cursor.execute("SELECT * FROM users WHERE username = ?", (user.username,))
            if cursor.fetchone():
                return False

        with self.db as cursor:
            cursor.execute(
                "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    user.username,
                    hashlib.sha256(self.embed_salt(user.password).encode()).hexdigest(),
                    user.fullname,
                    user.teachercode,
                    "student",
                    "",
                    user.group,
                    "",
                    0,
                ),
            )

        return True

    def login(self, user: UserCredentials) -> bool:
        """
        Checks if user exists and password is correct.
        :param user: user to check
        :return: True if user exists and password is correct, False otherwise
        """
        with self.db as cursor:
            cursor.execute(
                "SELECT * FROM users WHERE username = ? AND password = ?",
                (
                    user.username,
                    hashlib.sha256(self.embed_salt(user.password).encode()).hexdigest(),
                ),
            )
            return bool(cursor.fetchone())

    def session(self, username: str) -> str:
        """
        Create a new session for user.
        :param username: username of the user
        :return: session cookie
        """
        with self.db as cursor:
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            if not (user := cursor.fetchone()):
                return None

            return jwt.encode(
                {
                    "username": username,
                    "expires": int(time.time()) + 7 * 24 * 60 * 60,
                    "password_hash": user[1],
                },
                SECRET,
                algorithm="HS256",
            ).decode()

    def verify_session(self, session: str) -> typing.Union[User, bool]:
        """
        Verify session cookie.
        :param session: session cookie
        :return: fullname if session is valid, False otherwise
        """
        try:
            data = jwt.decode(session, SECRET, algorithms=["HS256"])
        except jwt.exceptions.DecodeError:
            return False

        if data["expires"] < int(time.time()):
            return False

        with self.db as cursor:
            cursor.execute(
                "SELECT * FROM users WHERE username = ?",
                (data["username"],),
            )
            if not (user := cursor.fetchone()):
                return False

            return User.from_tuple(user) if user[1] == data["password_hash"] else False

    def get_usergroups(self) -> typing.List[str]:
        """
        Get all usergroups.
        :return: list of usergroups
        """
        with self.db as cursor:
            cursor.execute("SELECT DISTINCT usergroup FROM users")
            return [
                usergroup[0]
                for usergroup in cursor.fetchall()
                if usergroup[0] != "teacher"
            ]

    def get_group_users(self, group: str) -> typing.List[User]:
        """
        Get all users from group.
        :return: list of users
        """
        with self.db as cursor:
            cursor.execute("SELECT * FROM users WHERE usergroup = ?", (group,))
            return [User.from_tuple(user) for user in cursor.fetchall()]

    def get_group_task(self, group: str) -> dict:
        """
        Get task from group.
        :return: task
        """
        with self.db as cursor:
            cursor.execute(
                "SELECT task, taskvars FROM users WHERE usergroup = ?", (group,)
            )
            res = cursor.fetchone()
            return (
                {"task": res[0], "taskvars": res[1]}
                if res
                else {"task": "", "taskvars": 0}
            )

    @staticmethod
    def sanitize_task(task: str) -> str:
        return re.sub(r"<.*?>", "", task)

    def set_group_task(self, group: str, task: str, taskvars: int) -> bool:
        """
        Set task for group.
        :param group: group to set task for
        :param task: task to set
        :param taskvars: number of variables in task
        :return: bool
        """
        with self.db as cursor:
            cursor.execute(
                (
                    "UPDATE users SET task = ?, taskvars = ?, taskstatus = ? WHERE"
                    " usergroup = ?"
                ),
                (self.sanitize_task(task), taskvars, "", group),
            )
            return True

    def delete_group_task(self, group: str) -> bool:
        """
        Delete task for group.
        :return: task
        """
        with self.db as cursor:
            cursor.execute(
                (
                    "UPDATE users SET task = ?, taskvars = ?, taskstatus = ? WHERE"
                    " usergroup = ?"
                ),
                ("", 0, "", group),
            )
            return True

    def set_done(self, user: User) -> bool:
        """
        Set task as done for user.
        :return: bool
        """
        with self.db as cursor:
            cursor.execute(
                "UPDATE users SET taskstatus = ? WHERE username = ?",
                ("done", user.username),
            )
            return True
