import sqlite3 as sqlite
import uuid
import json
import logging
from be.model import db_conn
from be.model import error
from sqlalchemy.exc import SQLAlchemyError
from be.model.postgresql import book, user, user_store, store, new_order, new_order_detail
from sqlalchemy.sql import and_
import datetime


class Buyer(db_conn.DBConn):
    # 连接数据库并建立会话
    def __init__(self):
        db_conn.DBConn.__init__(self)

    # 买家下单: 参数(买家用户ID; 商家ID; books数组,包含书籍ID和购买数量)
    def new_order(self, user_id: str, store_id: str, id_and_count: [(str, int)]) -> (int, str, str):
        order_id = ""

        try:
            # 检查用户Id和商家Id是否存在
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id) + (order_id,)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id) + (order_id,)
            uid = "{}_{}_{}".format(user_id, store_id, str(uuid.uuid1()))
            # print("uid",uid)
            # 对于每一件要购买的书: 先查找商家和书籍信息, 然后更新商家信息,订单细节表, 全部书籍查找结束后更新订单表
            for book_id, count in id_and_count:
                # 注意传入的book_id是str类型, 要转换为int类型
                book_id = int(book_id)
                # print("book_id",book_id)
                # 在商家表中查找商家id和书籍id
                row = self.session.query(store).filter_by(
                    book_id=book_id, store_id=store_id).first()
                # 不存在该书籍
                if row is None:
                    return error.error_non_exist_book_id(book_id) + (order_id,)

                # 库存量
                stock_level = row.stock_level
                # print("stock_level",stock_level)
                # 书籍信息(包含价格)
                book_info = row.book_info
                # print("book_info")
                book_info_json = json.loads(book_info)
                # 从书籍信息中取出价格
                price = book_info_json.get("price")
                # print("price",price)

                # 库存不足
                if stock_level < count:
                    return error.error_stock_level_low(book_id) + (order_id,)

                # 更新商家图书信息: 先找到待更新商家图书, 判断是否库存不足, 然后更新库存
                cursor = self.session.query(store).filter(store.book_id == book_id, store.store_id == store_id,
                                                          store.stock_level >= count).first()
                if cursor == None:
                    return error.error_stock_level_low(book_id) + (order_id,)
                cursor.stock_level -= count
                # print("stock_level",cursor.stock_level)
                self.session.add(cursor)


                # 更新订单细节表
                New_order_detail = new_order_detail(order_id=uid, book_id=book_id, count=count, price=price)
                self.session.add(New_order_detail)
                print(New_order_detail.order_id)

            # 更新订单表
            time = datetime.now().strftime("%Y-%m-%d %H:%M:%S") # 当前下单时间
            # ordered:已下单未付款 paid: 已付款未发货 delivered:已发货未收货   received:已收货 canceled:已取消
            status="ordered"

            New_order = new_order(order_id=uid, store_id=store_id, user_id=user_id,status="ordered",order_time=time)

            # print("New_order",New_order.store_id)
            self.session.add(New_order)
            self.session.commit()
            self.session.close()
            order_id = uid

        except SQLAlchemyError as e:
            print("{}".format(str(e)))
            logging.info("528, {}".format(str(e)))
            return 528, "{}".format(str(e)), ""
        except BaseException as e:
            print("{}".format(str(e)))
            logging.info("530, {}".format(str(e)))
            return 530, "{}".format(str(e)), ""

        return 200, "ok", order_id

    # 用户支付
    def payment(self, user_id: str, password: str, order_id: str) -> (int, str):
        try:
            # 根据订单id查找订单
            row = self.session.query(new_order).filter(new_order.order_id == order_id).first()
            if row is None:
                return error.error_invalid_order_id(order_id)

            order_id = row.order_id
            buyer_id = row.user_id
            store_id = row.store_id

            # 买家用户信息不一致
            if buyer_id != user_id:
                return error.error_authorization_fail()

            # 查找买家用户id
            row = self.session.query(user).filter(user.user_id == buyer_id).first()
            if row is None:
                return error.error_non_exist_user_id(buyer_id)
            balance = row.balance

            # 密码错误
            if password != row.password:
                return error.error_authorization_fail()

            # 查找user_store表
            row = self.session.query(user_store).filter(user_store.store_id == store_id).first()
            if row is None:
                return error.error_non_exist_store_id(store_id)

            # 卖家id
            seller_id = row.user_id
            if not self.user_id_exist(seller_id):
                return error.error_non_exist_user_id(seller_id)

            # 查找新订单, 计算总价看用户是否有足够余额支付
            cursor = self.session.query(new_order_detail).filter(new_order_detail.order_id == order_id).all()
            total_price = 0
            for row in cursor:
                count = row.count
                price = row.price
                total_price += price * count

            if balance < total_price:
                return error.error_not_sufficient_funds(order_id)

            # 买家余额更新
            cursor = self.session.query(user).filter(and_(user.user_id == buyer_id, user.balance >= total_price)).first()
            if cursor == None:
                return error.error_not_sufficient_funds(order_id)
            cursor.balance -= total_price
            self.session.add(cursor)

            # 卖家余额更新
            cursor = self.session.query(user).filter(user.user_id == seller_id).first()
            if cursor == None:
                return error.error_non_exist_user_id(seller_id)
            cursor.balance += total_price
            self.session.add(cursor)

            # 删除订单表数据
            cursor = self.session.query(new_order).filter(new_order.order_id == order_id)
            if cursor == None:
                return error.error_invalid_order_id(order_id)
            cursor.delete()    # 注意:delete的使用要求前面query不能加first

            # 删除订单细节表数据
            cursor = self.session.query(new_order_detail).filter(new_order_detail.order_id == order_id)
            if cursor == None:
                return error.error_invalid_order_id(order_id)
            cursor.delete()

            self.session.commit()

        except SQLAlchemyError as e:
            print("{}".format(str(e)))
            return 528, "{}".format(str(e))

        except BaseException as e:
            print("{}".format(str(e)))
            return 530, "{}".format(str(e))

        return 200, "ok"

    # 充值
    def add_funds(self, user_id, password, add_value) -> (int, str):
        try:
            # 判断用户密码是否输入正确
            row = self.session.query(user).filter(user.user_id == user_id).first()
            if row == None:
                return error.error_authorization_fail()

            if row.password != password:
                return error.error_authorization_fail()

            # 更新用户余额
            cursor = self.session.query(user).filter(user.user_id == user_id).first()
            if cursor == None:
                return error.error_non_exist_user_id(user_id)
            cursor.balance += add_value
            self.session.add(cursor)

            self.session.commit()

        except SQLAlchemyError as e:
            print("{}".format(str(e)))
            return 528, "{}".format(str(e))
        except BaseException as e:
            print("{}".format(str(e)))
            return 530, "{}".format(str(e))

        return 200, "ok"
