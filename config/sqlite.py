"""sqlite3功能区"""
import sqlite3
import pendulum


class User:
    def __init__(self) -> None:
        self.conn = sqlite3.connect("config/user.db")
        self.cur = self.conn.cursor()

        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS users (username TEXT, password BINARY, register_date DATE)"
        )

    def user_register(self, username: str, password: str):
        register_date = str(pendulum.now())
        user_input = (
            "INSERT INTO users (username, password, register_date) VALUES (?, ?, ?)"
        )

        self.cur.execute(user_input, (username, password, register_date))

        self.conn.commit()
        self.conn.close()

    def user_info(self, username: str):
        self.cur.execute("SELECT password FROM users WHERE username = ?", (username,))
        row = self.cur.fetchone()
        if row:
            return row[0]

    def users_check(self):
        self.cur.execute("SELECT * FROM users")
        rows = self.cur.fetchall()
        users = [row[0] for row in rows]
        return users
