import sqlite3 as sqlite
import random
from be.model import error
from be.model import db_conn
from be.model.postgresql import book, store, user, new_order, user_store
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime


class Seller(db_conn.DBConn):

    def __init__(self):
        db_conn.DBConn.__init__(self)

    def add_book(self, user_id: str, store_id: str, book_id: str, book_json_str: str, stock_level: int):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if self.book_id_exist(store_id, book_id):
                return error.error_exist_book_id(book_id)

            # self.conn.execute("INSERT into store(store_id, book_id, book_info, stock_level)"
            # "VALUES (?, ?, ?, ?)", (store_id, book_id, book_json_str, stock_level))
            # self.conn.commit()
            # store1 = self.session.query(store).filter_by(store_id=store_id).first()
            # if store1 is None:
            #     return error.error_non_exist_store_id(store_id)
            # store1.book_id = book_id
            store1 = store(store_id=store_id, book_id=book_id, book_info=book_json_str, stock_level=stock_level)
            self.session.add(store1)
            self.session.commit()
            self.session.close()
        except SQLAlchemyError as e:
            print("{}".format(str(e)))
            return 528, "{}".format(str(e))
        except BaseException as e:
            print("{}".format(str(e)))
            return 530, "{}".format(str(e))
        return 200, "ok"

    def add_stock_level(self, user_id: str, store_id: str, book_id: str, add_stock_level: int):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if not self.book_id_exist(store_id, book_id):
                return error.error_non_exist_book_id(book_id)
            storel = self.session.query(store).filter_by(store_id=store_id
                                                         , book_id=book_id).first()
            storel.stock_level += add_stock_level
            # self.conn.execute("UPDATE store SET stock_level = stock_level + ? "
            # "WHERE store_id = ? AND book_id = ?", (add_stock_level, store_id, book_id))
            # self.conn.commit()
            self.session.commit()
            self.session.close()
        except SQLAlchemyError as e:
            print("{}".format(str(e)))
            return 528, "{}".format(str(e))
        except BaseException as e:
            print("{}".format(str(e)))
            return 530, "{}".format(str(e))
        return 200, "ok"

    def deliver_order(self, user_id: str, order_id: str):
        try:
            # 判断该用户是否存在
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id) + (order_id,)

            order = self.session.query(new_order).filter_by(order_id=order_id, status="paid").first()
            if order is None:
                return error.error_invalid_order_id(order_id)

            store_id = order.store_id
            # 判断买家身份是否一致
            query = self.session.query(user_store).filter_by(store_id=store_id).first()
            seller_id = query.user_id
            if seller_id != user_id:
                return error.error_authorization_fail()

            # 修改订单状态为已发货
            order.status="delivered"
            self.session.add(order)
            self.session.commit()

        except SQLAlchemyError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"


    def create_store(self, user_id: str, store_id: str) -> (int, str):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if self.store_id_exist(store_id):
                return error.error_exist_store_id(store_id)
            # self.conn.execute("INSERT into user_store(store_id, user_id)"
            #                  "VALUES (?, ?)", (store_id, user_id))
            # self.conn.commit()
            # row = self.session.query(store).filter_by(store_id=store_id).first()
            # if row:
            #     return error.error_exist_store_id(store_id)
            usr_store1 = user_store(store_id=store_id, user_id=user_id)
            self.session.add(usr_store1)
            self.session.commit()
            self.session.close()
        except SQLAlchemyError as e:
            print("{}".format(str(e)))
            return 528, "{}".format(str(e))
        except BaseException as e:
            print("{}".format(str(e)))
            return 530, "{}".format(str(e))
        return 200, "ok"
