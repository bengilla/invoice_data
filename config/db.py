"""sqlite3功能区"""
import sqlite3


class User:
    def __init__(self) -> None:
        self.conn_DB = sqlite3.connect("db/user.db")
        self.cur = self.conn_DB.cursor()

        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS users (username TEXT, password BINARY)"
        )

    def user_register(self, username: str, password: str):
        user_input = "INSERT INTO users (username, password) VALUES (?, ?)"

        self.cur.execute(user_input, (username, password))

        self.conn_DB.commit()
        self.conn_DB.close()

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


class Invoice:
    def __init__(self) -> None:
        self.conn_DB = sqlite3.connect("db/invoice.db")
        self.cur = self.conn_DB.cursor()

        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS invoice (id INT, date TEXT, company TEXT, amount FLOAT, pdf BINARY, download BOOLEAN)"
        )
