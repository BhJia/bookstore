import logging
import os
import sqlite3 as sqlite
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import Column, create_engine, Integer, Text, LargeBinary, ForeignKey

# engine = create_engine('postgresql+psycopg2://postgres:12345678@localhost/bookstore', encoding='utf-8',
#                        echo=True)
# DbSession = sessionmaker(bind=engine)
# Base = declarative_base()


# # 用户表
# class user():
#     __tablename__ = 'usr'
#     user_id = Column(Text, primary_key=True, unique=True)
#     password = Column(Text, nullable=False)
#     balance = Column(Integer, nullable=False)
#     token = Column(Text, nullable=False)
#     terminal = Column(Text, nullable=False)


class Store:
    database: str

    def __init__(self, db_path):
        self.session = DbSession()
        self.Base = Base

    def init_tables(self):
        try:
            session = self.get_db_session()
            session.execute(
                "CREATE TABLE IF NOT EXISTS user ("
                "user_id TEXT PRIMARY KEY, password TEXT NOT NULL, "
                "balance INTEGER NOT NULL, token TEXT, terminal TEXT);"
            )

            session.execute(
                "CREATE TABLE IF NOT EXISTS user_store("
                "user_id TEXT, store_id, PRIMARY KEY(user_id, store_id));"
            )

            session.execute(
                "CREATE TABLE IF NOT EXISTS store( "
                "store_id TEXT, book_id TEXT, book_info TEXT, stock_level INTEGER,"
                " PRIMARY KEY(store_id, book_id))"
            )

            session.execute(
                "CREATE TABLE IF NOT EXISTS new_order( "
                "order_id TEXT PRIMARY KEY, user_id TEXT, store_id TEXT)"
            )

            session.execute(
                "CREATE TABLE IF NOT EXISTS new_order_detail( "
                "order_id TEXT, book_id TEXT, count INTEGER, price INTEGER,  "
                "PRIMARY KEY(order_id, book_id))"
            )

            session.commit()
        except SQLAlchemyError as e:
            logging.error(e)
            session.rollback()

    def get_db_session(self):
        return self.session


database_instance: Store = None


def init_database(db_path):
    global database_instance
    database_instance = Store(db_path)


def get_db_conn():
    global database_instance
    return database_instance.get_db_conn()
