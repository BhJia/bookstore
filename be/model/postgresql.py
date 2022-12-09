from sqlalchemy import Column, create_engine, Integer, Text, LargeBinary, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import sqlite3 as sqlite

# 建立连接('postgresql+psycopg2://postgres:密码@localhost/数据库名称')
engine = create_engine('postgresql+psycopg2://postgres:12345678@localhost/bookstore', encoding='utf-8', echo=True)
# 建立会话
DbSession = sessionmaker(bind=engine)
# 创建对象的基类
Base = declarative_base()


def init_database():
    # 建立连接('postgresql+psycopg2://postgres:密码@localhost/数据库名称')
    engine = create_engine('postgresql+psycopg2://postgres:12345678@localhost/bookstore', encoding='utf-8', echo=True)
    # 建立会话
    DbSession = sessionmaker(bind=engine)
    # 创建对象的基类
    Base = declarative_base()


# 定义原始的图书表(按照markdown文件中的Schema)
class book(Base):
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


# 用户表
class user(Base):
    __tablename__ = 'user'
    user_id = Column(Text, primary_key=True, unique=True, index=True)
    password = Column(Text, nullable=False)
    balance = Column(Integer, nullable=False)
    token = Column(Text, nullable=False)
    terminal = Column(Text, nullable=False)


# 用户商店关系表
class user_store(Base):
    __tablename__ = 'user_store'
    user_id = Column(Text, ForeignKey('user.user_id'), primary_key=True, nullable=False, index=True)
    store_id = Column(Text, primary_key=True, nullable=False, unique=True, index=True)


# 商店表
class store(Base):
    __tablename__ = 'store'
    store_id = Column(Text, ForeignKey('user_store.store_id'), primary_key=True, nullable=False, index=True)
    book_id = Column(Integer, ForeignKey('book.id'), primary_key=True, nullable=False)
    book_info = Column(Text, nullable=True)
    stock_level = Column(Integer, nullable=True)


# 订单表和订单细节表的区别: 订单表存储的是一个订单的整体信息, 订单细节表存储的是一个订单里面所有购买书籍的信息
# 因此用户购买一次书籍, 订单表只有一条记录, 而订单细节表有多条记录
# 订单表
class new_order(Base):
    __tablename__ = 'new_order'
    order_id = Column(Text, primary_key=True, index=True)
    user_id = Column(Text, ForeignKey('user.user_id'), nullable=False)
    store_id = Column(Text, ForeignKey('user_store.store_id'), nullable=False)
    price = Column(Integer, nullable=False)  # 取消订单后返还金额
    status = Column(Text, nullable=False)
    order_time = Column(DateTime, nullable=False)
    pay_time = Column(DateTime, nullable=True)


# ordered:已下单未付款 paid: 已付款未发货 delivered:已发货未收货   received:已收货 canceled:已取消
# 订单细节表
class new_order_detail(Base):
    __tablename__ = 'new_order_detail'
    order_id = Column(Text, ForeignKey('new_order.order_id'), primary_key=True, nullable=False, index=True)
    book_id = Column(Integer, ForeignKey('book.id'), primary_key=True, nullable=False)
    count = Column(Integer, nullable=False)
    price = Column(Integer, nullable=False)


# 创建表格
def createTable():
    # 创建所有继承于Base的类对应的表
    Base.metadata.create_all(engine)


# 插入数据(将sqlite数据库的数据转存到postgresql中)
def insertData():
    # 建立一个会话
    session = DbSession()
    # 连接sqlite数据库book.db
    conn = sqlite.connect("../../fe/data/book.db")
    # 在book.db中提取数据
    cursor = conn.execute(
        "SELECT id, title, author, "
        "publisher, original_title, "
        "translator, pub_year, pages, "
        "price, currency_unit, binding, "
        "isbn, author_intro, book_intro, "
        "content, tags FROM book"
    )

    # 将数据存储到一个新对象中, 并将对象插入postgresql数据库的Book表中
    for i in cursor:
        new_book = book(id=i[0], title=i[1], author=i[2], publisher=i[3], original_title=i[4], translator=i[5],
                        pub_year=i[6], pages=i[7], price=i[8], binding=i[9], isbn=i[10], author_intro=i[11],
                        book_intro=i[12], content=i[13], tags=i[14])
        # 添加到session
        session.add(new_book)
        # 提交即保存到数据库
        session.commit()

    # 关闭session
    session.close()


def deleteAllData():
    session = DbSession()  # 创建会话
    delete_user = session.query(user).delete()
    delete_user_store = session.query(user_store).delete()
    delete_store = session.query(store).delete()
    session.commit()
    session.close()  # 关闭会话


def deleteTables():
    Base.metadata.drop_all(engine)


if __name__ == '__main__':
    deleteTables()
    createTable()
    insertData()
