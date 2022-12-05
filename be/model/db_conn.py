from be.model import store
from sqlalchemy import Column, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import sqlite3 as sqlite
from be.model.postgresql import book, user, user_store, store, new_order, new_order_detail
from sqlalchemy.sql import and_


# 把原来用sqlite写的一些判断id是否存在的函数改为用postgresql写的
class DBConn:
    # 连接postgresql数据库, 建立会话
    def __init__(self):
        engine = create_engine('postgresql+psycopg2://postgres:12345678@localhost/bookstore', encoding='utf-8',
                               echo=True)
        DbSession = sessionmaker(bind=engine)
        self.session = DbSession()
        self.Base = declarative_base()

    # 判断给定的user_id是否存在
    def user_id_exist(self, user_id):
        # session.query查找user表中是否存在给定的user_id
        row = self.session.query(user).filter_by(user_id=user_id).first()
        if row is None:
            return False
        else:
            return True

    # 判断给定的store_id和book_id是否存在
    def book_id_exist(self, store_id, book_id):
        row = self.session.query(store).filter_by(store_id=store_id, book_id=book_id).first()
        if row is None:
            return False
        else:
            return True

    # 判断给定的store_id是否存在
    def store_id_exist(self, store_id):
        row = self.session.query(user_store).filter_by(store_id=store_id).first()
        if row is None:
            return False
        else:
            return True
