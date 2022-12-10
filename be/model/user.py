import jwt
import time
import logging
import sqlite3 as sqlite
from be.model import error
from be.model import db_conn
from be.model.postgresql import book, store, user, user_store
from be.model.searchpostgresql import Search_book_intro, Search_title, Search_author
from sqlalchemy.exc import SQLAlchemyError
import sqlalchemy


def jwt_encode(user_id: str, terminal: str) -> str:
    encoded = jwt.encode(
        {"user_id": user_id, "terminal": terminal, "timestamp": time.time()},
        key=user_id,
        algorithm="HS256",
    )
    return encoded.encode("utf-8").decode("utf-8")


def jwt_decode(encoded_token, user_id: str) -> str:
    decoded = jwt.decode(encoded_token, key=user_id, algorithms="HS256")
    return decoded


class User(db_conn.DBConn):
    token_lifetime: int = 3600  # 3600 second

    def __init__(self):
        db_conn.DBConn.__init__(self)

    def __check_token(self, user_id, db_token, token) -> bool:
        try:
            if db_token != token:
                return False
            jwt_text = jwt_decode(encoded_token=token, user_id=user_id)
            ts = jwt_text["timestamp"]
            if ts is not None:
                now = time.time()
                if self.token_lifetime > now - ts >= 0:
                    return True
        except jwt.exceptions.InvalidSignatureError as e:
            logging.error(str(e))
            print(str(e))
            return False

    def register(self, user_id: str, password: str):
        try:
            if self.user_id_exist(user_id):
                return error.error_exist_user_id(user_id)
            terminal = "terminal_{}".format(str(time.time()))
            token = jwt_encode(user_id, terminal)
            new_usr = user(
                user_id=user_id,
                password=password,
                balance=0,
                token=token,
                terminal=terminal
            )
            self.session.add(new_usr)
            self.session.commit()
        except SQLAlchemyError:
            return error.error_exist_user_id(user_id)
        return 200, "ok"

    def check_token(self, user_id: str, token: str) -> (int, str):
        row = self.session.query(user).filter(user.user_id == user_id).first()
        if row == None:
            return error.error_authorization_fail()
        db_token = row.token
        if not self.__check_token(user_id, db_token, token):
            return error.error_authorization_fail()
        return 200, "ok"

    def check_password(self, user_id: str, password: str) -> (int, str):
        row = self.session.query(user).filter(user.user_id == user_id).first()
        if row == None:
            return error.error_authorization_fail()

        if password != row.password:
            return error.error_authorization_fail()

        return 200, "ok"

    def login(self, user_id: str, password: str, terminal: str) -> (int, str, str):
        token = ""
        try:
            code, message = self.check_password(user_id, password)
            if code != 200:
                return code, message, ""

            token = jwt_encode(user_id, terminal)
            cursor = self.session.query(user).filter(user.user_id == user_id).first()
            if cursor == None:
                return error.error_authorization_fail() + ("",)
            cursor.token = token
            cursor.terminal = terminal
            self.session.commit()
        except SQLAlchemyError as e:
            print("{}".format(str(e)))
            return 528, "{}".format(str(e)), ""
        except BaseException as e:
            print("{}".format(str(e)))
            return 530, "{}".format(str(e)), ""
        return 200, "ok", token

    def logout(self, user_id: str, token: str) -> bool:
        try:
            code, message = self.check_token(user_id, token)
            if code != 200:
                return code, message

            terminal = "terminal_{}".format(str(time.time()))
            new_token = jwt_encode(user_id, terminal)

            cursor = self.session.query(user).filter(user.user_id == user_id).first()

            if cursor is None:
                return error.error_authorization_fail()

            cursor.token = new_token
            cursor.terminal = terminal
            self.session.commit()
        except SQLAlchemyError as e:
            print("{}".format(str(e)))
            return 528, "{}".format(str(e))
        except BaseException as e:
            print("{}".format(str(e)))
            return 530, "{}".format(str(e))
        return 200, "ok"

    def unregister(self, user_id: str, password: str) -> (int, str):
        try:
            code, message = self.check_password(user_id, password)
            if code != 200:
                return code, message

            query = self.session.query(user).filter(user.user_id == user_id)
            query.delete()

            if query.first() is None:
                self.session.commit()
            else:
                return error.error_authorization_fail()

        except SQLAlchemyError as e:
            print("{}".format(str(e)))
            return 528, "{}".format(str(e))
        except BaseException as e:
            print("{}".format(str(e)))
            return 530, "{}".format(str(e))
        return 200, "ok"

    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        try:
            code, message = self.check_password(user_id, old_password)
            if code != 200:
                return code, message

            terminal = "terminal_{}".format(str(time.time()))
            token = jwt_encode(user_id, terminal)

            cursor = self.session.query(user).filter(user.user_id == user_id).first()
            if cursor == None:
                return error.error_authorization_fail()
            cursor.password = new_password
            cursor.token = token
            cursor.terminal = terminal
            self.session.commit()
        except SQLAlchemyError as e:
            print("{}".format(str(e)))
            return 528, "{}".format(str(e))
        except BaseException as e:
            print("{}".format(str(e)))
            return 530, "{}".format(str(e))
        return 200, "ok"

    def search_author(self, author: str, page: str):  # 200,'ok',list[{str,str,str,str,list,bytes}]
        try:

            ret = []

            # records = self.session.execute(
            #    " SELECT title,book.author,publisher,book_intro,tags,picture "
            #    "FROM book WHERE id in "
            #    "(select id from search_author where author='%s' and search_id BETWEEN %d and %d)" % (
            #    author, 10 * page - 10, 10 * page - 1)).fetchall()
            print("1")
            id1 = self.session.query(Search_author).all()
            print(2)
            page = int(page)
            records = self.session.query(book).join(Search_author, Search_author.id == book.id).filter(
                Search_author.author == author, Search_author.search_id >= 10 * page - 10,
                Search_author.search_id <= 10 * page - 1).all()
            print(3)
            #

            #
            #
            #
            #
            # if records is None:
            #     return error.error_cannot_find_book()
            #
            #
            # for row in records:
            #     title = row.title
            #     print(title)
            #
            #     author1 = row.author
            #     print(author1)
            #
            #     publisher = row.publisher
            #     book_intro = row.book_intro
            #     tags = row.tags
            #     ret.append(
            #         {'title': title, 'author': author1, 'publisher': publisher,
            #          'book_intro': book_intro,
            #          'tags': tags, 'picture': ''})

        except SQLAlchemyError as e:
            print("{}".format(str(e)))
            return 528, "{}".format(str(e))
        except BaseException as e:
            print("{}".format(str(e)))
            return 530, "{}".format(str(e))
        return 200, "ok"
