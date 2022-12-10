from sqlalchemy import Column, create_engine, Integer, Text, LargeBinary, ForeignKey, DateTime, PrimaryKeyConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import sqlite3 as sqlite
import jieba.analyse
from jieba import cut_for_search
import re

import time
import datetime
# 建立连接('postgresql+psycopg2://postgres:密码@localhost/数据库名称')
engine = create_engine('postgresql+psycopg2://postgres:12345678@localhost/bookstore', encoding='utf-8', echo=True)
# 建立会话
DbSession = sessionmaker(bind=engine)
# 创建对象的基类
Base = declarative_base()


class Book(Base):
    __tablename__ = 'book'
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(Text, nullable=False)
    author = Column(Text, nullable=True)
    publisher = Column(Text, nullable=True)
    original_title = Column(Text, nullable=True)
    translator = Column(Text, nullable=True)
    pub_year = Column(Text, nullable=True)
    pages = Column(Integer, nullable=True)
    price = Column(Integer, nullable=True)
    binding = Column(Text, nullable=True)
    isbn = Column(Text, nullable=True)
    author_intro = Column(Text, nullable=True)
    book_intro = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)
    # LargeBinary类型可以存储Blob类型文件
    picture = Column(LargeBinary, nullable=True)


# 搜索标题表
class Search_title(Base):
    __tablename__ = 'search_title'
    search_id = Column(Integer, nullable=False)
    title = Column(Text, nullable=False)
    id = Column(Integer, ForeignKey('book.id'), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint('search_id', 'title'),
        {},
    )





# 搜索作者表
class Search_author(Base):
    __tablename__ = 'search_author'
    search_id = Column(Integer, nullable=False)
    author = Column(Text, nullable=False)
    id = Column(Integer, ForeignKey('book.id'), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint('search_id', 'author'),
        {},
    )




# 搜索书本内容表
class Search_book_intro(Base):
    __tablename__ = 'search_book_intro'
    search_id = Column(Integer, nullable=False)
    book_intro = Column(Text, nullable=False)
    id = Column(Integer, ForeignKey('book.id'), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint('search_id', 'book_intro'),
        {},
    )
def delete():
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    sql=session.execute("DROP TABLE book CASCADE")

    session.commit()
    session.close()



def insert_author():
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    Base.metadata.create_all(engine)
    row = session.execute("SELECT id, author FROM book;").fetchall()
    for i in row:
        tmp = i.author
        if tmp == None:
            j = '作者不详'
            max_num = session.execute(
                "SELECT MAX(search_id) FROM search_author WHERE author = '%s';"
                % (j, )).fetchone()
            max_num = max_num[0]
            if max_num == None:
                max_num = 0
            else:
                max_num += 1
            # print(max_num, j, i.book_id)
            session.execute(
                "INSERT into search_author(search_id, author, id) VALUES (%d, '%s', %d)"
                % (max_num, j, int(i.id)))

        else:
            tmp = re.sub(r'[\(\[\{（【][^)）】]*[\)\]\{\】\）]\s?', '', tmp)
            tmp = re.sub(r'[^\w\s]', '', tmp)
            length = len(tmp)
            for k in range(1, length + 1):
                if tmp[k - 1] == '':
                    continue
                j = tmp[:k]
                max_num = session.execute(
                    "SELECT MAX(search_id) FROM search_author WHERE author = '%s';"
                    % (j, )).fetchone()
                max_num = max_num[0]
                if max_num == None:
                    max_num = 0
                else:
                    max_num += 1
                # print(max_num, j, i.book_id)
                session.execute(
                    "INSERT into search_author(search_id, author, id) VALUES (%d, '%s', %d)"
                    % (max_num, j, int(i.id)))
    session.commit()


def insert_title():
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    Base.metadata.create_all(engine)
    row = session.execute("SELECT id, title FROM book;").fetchall()
    for i in row:
        tmp = i.title
        # print(tmp)
        tmp = re.sub(r'[\(\[\{（【][^)）】]*[\)\]\{\】\）]\s?', '', tmp)
        tmp = re.sub(r'[^\w\s]', '', tmp)
        # 处理空标题
        if len(tmp) == 0:
            continue

        # 搜索引擎模式，在精确模式的基础上，对长词再次切分，提高召回率，适合用于搜索引擎分词。
        seg_list = cut_for_search(tmp)
        sig_list = []
        tag = 0
        for k in seg_list:
            sig_list.append(k)
            if k == tmp:
                tag = 1
        if tag == 0:
            sig_list.append(tmp)

        for j in sig_list:
            if j == "" or j == " ":
                continue
            max_num = session.execute(
                "SELECT MAX(search_id) FROM search_title WHERE title = '%s';" %
                (j, )).fetchone()
            max_num = max_num[0]
            if max_num == None:
                max_num = 0
            else:
                max_num += 1
            # print(max_num, j, i.book_id)
            session.execute(
                "INSERT into search_title(search_id, title, id) VALUES (%d, '%s', %d)"
                % (max_num, j, int(i.id)))
    session.commit()




def insert_book_intro():
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    Base.metadata.create_all(engine)
    row = session.execute("SELECT id, book_intro FROM book;").fetchall()
    for i in row:
        tmp = i.book_intro
        if tmp != None:
            # print(tmp)
            # 采用textrank进行分词
            keywords_textrank = jieba.analyse.textrank(tmp)
            # print(keywords_textrank)
            # keywords_tfidf = jieba.analyse.extract_tags(tmp)
            # print(keywords_tfidf)
            for j in keywords_textrank:
                max_num = session.execute(
                    "SELECT MAX(search_id) FROM search_book_intro WHERE book_intro = '%s';"
                    % (j, )).fetchone()
                max_num = max_num[0]
                if max_num == None:
                    max_num = 0
                else:
                    max_num += 1
                # print(max_num, j, i.book_id)
                session.execute(
                    "INSERT into search_book_intro(search_id, book_intro, id) VALUES (%d, '%s', %d)"
                    % (max_num, j, int(i.id)))
    session.commit()


def init():
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    Base.metadata.create_all(engine)
    # 提交即保存到数据库
    session.commit()
    # 关闭session
    session.close()

def deleteTables():
    Base.metadata.drop_all(engine)


if __name__ == "__main__":
    # 创建数据库

    # 插入表
    # delete()
    # deleteTables()
    start = datetime.datetime.now()

    insert_author()
    insert_title()
    insert_book_intro()
    end = datetime.datetime.now()
    print("spend {} sec".format((end - start).seconds))