import sqlite3 as sqlite
import uuid
import json
import logging
import time
from be.model import db_conn
from be.model import error
from sqlalchemy import Column
from sqlalchemy.exc import SQLAlchemyError
from be.model.postgresql import book, user, user_store, store, new_order, new_order_detail
from sqlalchemy.sql import and_
from datetime import datetime


class Buyer(db_conn.DBConn):
    # 连接数据库并建立会话
    def __init__(self):
        db_conn.DBConn.__init__(self)

    # 买家下单
    def new_order(self, user_id: str, store_id: str, id_and_count: [(str, int)]) -> (int, str, str):
        order_id = ""

        try:
            # 检查用户id和商家id是否存在
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id) + (order_id,)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id) + (order_id,)
            # 生成每个用户id和商家id的标识符uid
            uid = "{}_{}_{}".format(user_id, store_id, str(uuid.uuid1()))
            # print("uid",uid)
            # 对于每一件要购买的书: 先查找商家和书籍信息, 然后更新商家信息,订单细节表, 全部书籍查找结束后更新订单表
            total_price = 0
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
                total_price += price

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

            # 更新订单表
            time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # 当前下单时间
            # ordered:已下单未付款 paid: 已付款未发货 delivered:已发货未收货   received:已收货 canceled:已取消
            status = "ordered"

            New_order = new_order(order_id=uid, store_id=store_id, user_id=user_id, status="ordered", price=total_price,
                                  order_time=time)

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
            # 根据订单id查找订单, 判断订单是否存在
            # print("1")
            row = self.session.query(new_order).filter(new_order.order_id == order_id).first()
            if row is None:
                return error.error_invalid_order_id(order_id)

            order_id = row.order_id
            buyer_id = row.user_id
            store_id = row.store_id

            # 买家用户信息不一致
            if buyer_id != user_id:
                return error.error_authorization_fail()
            # print("2")
            # 查找买家用户
            row = self.session.query(user).filter(user.user_id == buyer_id).first()
            if row is None:
                return error.error_non_exist_user_id(buyer_id)
            balance = row.balance

            # 密码错误
            if password != row.password:
                return error.error_authorization_fail()

            # print("3")
            # 查找user_store表判断店铺是否存在
            row = self.session.query(user_store).filter(user_store.store_id == store_id).first()
            if row is None:
                return error.error_non_exist_store_id(store_id)

            # 判断卖家id是否存在
            seller_id = row.user_id
            if not self.user_id_exist(seller_id):
                return error.error_non_exist_user_id(seller_id)

            # 查找新订单, 计算总价看用户是否有足够余额支付
            # print("4")
            cursor = self.session.query(new_order_detail).filter(new_order_detail.order_id == order_id).all()
            total_price = 0
            for row in cursor:
                count = row.count
                price = row.price
                total_price += price * count

            if balance < total_price:
                return error.error_not_sufficient_funds(order_id)

            # 更新订单总价格
            # print("5")
            cursor = self.session.query(new_order).filter(new_order.order_id == order_id).first()
            cursor.price += total_price
            self.session.add(cursor)

            # 买家余额更新
            # print("6")
            cursor = self.session.query(user).filter(
                and_(user.user_id == buyer_id, user.balance >= total_price)).first()
            if cursor == None:
                return error.error_not_sufficient_funds(order_id)
            cursor.balance -= total_price
            self.session.add(cursor)

            # 更新订单表数据
            # print("7")
            time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # 当前下单时间
            cursor = self.session.query(new_order).filter(new_order.order_id == order_id).first()
            if cursor == None:
                return error.error_invalid_order_id(order_id)
            cursor.status = "paid"
            cursor.pay_time = time
            # print("8")
            self.session.add(cursor)
            self.session.commit()
            self.session.close()

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
            # 判断用户是否存在,密码是否输入正确
            row = self.session.query(user).filter(user.user_id == user_id).first()
            if row == None:
                return error.error_non_exist_user_id(user_id)
            if row.password != password:
                return error.error_authorization_fail()

            # 更新用户余额
            row.balance += add_value
            self.session.add(row)
            self.session.commit()
            self.session.close()

        except SQLAlchemyError as e:
            print("{}".format(str(e)))
            return 528, "{}".format(str(e))
        except BaseException as e:
            print("{}".format(str(e)))
            return 530, "{}".format(str(e))

        return 200, "ok"

    # 收货
    def receive_order(self, user_id: str, order_id: str):
        try:
            # print("1")
            # 判断该用户是否存在
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id) + (order_id,)

            # print("2")
            # 判断该订单是否在配送中
            row = self.session.query(new_order).filter_by(status="delivered", order_id=order_id).first()
            if row is None:
                return error.error_invalid_order_id(order_id)

            # print("3")
            # 判断用户id和买家id是否一致
            buyer_id = row.user_id
            if user_id != buyer_id:
                return error.error_authorization_fail()

            # 商店ID
            storeID = row.store_id
            # 订单总价格
            total_price = row.price

            # print("4")
            # 查找user_store表
            row = self.session.query(user_store).filter(user_store.store_id == storeID).first()
            if row is None:
                return error.error_non_exist_store_id(storeID)

            # 卖家id
            seller_id = row.user_id
            if not self.user_id_exist(seller_id):
                return error.error_non_exist_user_id(seller_id)

            # print("5")
            # 卖家余额更新
            cursor = self.session.query(user).filter(user.user_id == seller_id).first()
            if cursor == None:
                return error.error_non_exist_user_id(seller_id)
            cursor.balance += total_price
            # print("6")
            self.session.add(cursor)
            self.session.commit()
            self.session.close()

        except SQLAlchemyError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))

        return 200, "ok"

    # 历史订单
    def history_order(self, buyer_id: str, status: str):
        try:
            # 检查用户是否存在
            if not self.user_id_exist(buyer_id):
                return error.error_non_exist_user_id(buyer_id)

            # 查所有订单
            if status == "all":
                ordered = self.session.query(new_order).filter_by(user_id=buyer_id).all()
                order_info = []
                for order in ordered:
                    order_info1 = []
                    info = self.session.query(new_order_detail).filter_by(order_id=order.order_id).all()
                    for i in info:
                        order_info1.append({
                            "order_id": i.order_id,
                            "book_id": i.book_id,
                            "count": i.count,
                            "price": i.price
                        })
                    order_info.append(order_info1)
                self.session.close()

            # 已下单未付款
            if status == "ordered":
                ordered = self.session.query(new_order).filter_by(status="ordered", user_id=buyer_id).all()
                order_info = []
                for order in ordered:
                    order_info1 = []
                    info = self.session.query(new_order_detail).filter_by(order_id=order.order_id).all()
                    for i in info:
                        order_info1.append({
                            "order_id": i.order_id,
                            "book_id": i.book_id,
                            "count": i.count,
                            "price": i.price
                        })
                    order_info.append(order_info1)
                self.session.close()

            # 已付款待发货
            if status == "paid":
                ordered = self.session.query(new_order).filter_by(status="paid", user_id=buyer_id).all()
                order_info = []
                for order in ordered:
                    order_info1 = []
                    info = self.session.query(new_order_detail).filter_by(order_id=order.order_id).all()
                    for i in info:
                        order_info1.append({
                            "order_id": i.order_id,
                            "book_id": i.book_id,
                            "count": i.count,
                            "price": i.price
                        })
                    order_info.append(order_info1)
                self.session.close()

            # 已发货未收货
            if status == "delivered":
                ordered = self.session.query(new_order).filter_by(status="delivered", user_id=buyer_id).all()
                order_info = []
                for order in ordered:
                    order_info1 = []
                    info = self.session.query(new_order_detail).filter_by(order_id=order.order_id).all()
                    for i in info:
                        order_info1.append({
                            "order_id": i.order_id,
                            "book_id": i.book_id,
                            "count": i.count,
                            "price": i.price
                        })
                    order_info.append(order_info1)
                self.session.close()

            # 已收货
            if status == "received":
                ordered = self.session.query(new_order).filter_by(status="received", user_id=buyer_id).all()
                order_info = []
                for order in ordered:
                    order_info1 = []
                    info = self.session.query(new_order_detail).filter_by(order_id=order.order_id).all()
                    for i in info:
                        order_info1.append({
                            "order_id": i.order_id,
                            "book_id": i.book_id,
                            "count": i.count,
                            "price": i.price
                        })
                    order_info.append(order_info1)
                self.session.close()

            # 取消的订单
            if status == "canceled":
                ordered = self.session.query(new_order).filter_by(status="canceled", user_id=buyer_id).all()
                order_info = []
                for order in ordered:
                    order_info1 = []
                    info = self.session.query(new_order_detail).filter_by(order_id=order.order_id).all()
                    for i in info:
                        order_info1.append({
                            "order_id": i.order_id,
                            "book_id": i.book_id,
                            "count": i.count,
                            "price": i.price
                        })
                    order_info.append(order_info1)
                self.session.close()
        except SQLAlchemyError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok", order_info

    # 取消订单
    def cancel_order(self, buyer_id: str, order_id: str):
        try:
            # 判断用户是否存在
            if not self.user_id_exist(buyer_id):
                return error.error_non_exist_user_id(buyer_id)

            # 是否属于未付款订单
            # print("1")
            stored = self.session.query(new_order).filter_by(status="ordered", user_id=buyer_id,
                                                             order_id=order_id).first()
            if stored == None:
                # print("2")
                # 是否属于已付款且未发货订单
                order1 = self.session.query(new_order).filter_by(status="paid", order_id=order_id).first()
                if order1 == None:
                    # print("3")
                    return error.error_invalid_order_id(order_id)
                store_id = order1.store_id
                price = order1.price

                # 修改订单状态
                order1.status = "canceled"
                self.session.add(order1)

                # 买家退款
                # print("4")
                cursor = self.session.query(user).filter_by(user_id=buyer_id).first()
                if cursor == None:
                    return error.error_non_exist_user_id(buyer_id)
                cursor.balance += price
                self.session.add(cursor)
                self.session.commit()

            else:
                # print("5")
                stored.status = "canceled"
                self.session.add(stored)
                self.session.commit()

            # 增加库存
            # 查store取出book_id
            # print("6")
            store1 = self.session.query(store).filter_by(store_id=store_id).first()
            if store1 == None:
                return error.error_non_exist_store_id(store_id)

            # 查订单细节更新库存(注意一个订单可能不止一个子订单, 需要遍历所有子订单增加库存)
            # print("7")
            cursor = self.session.query(new_order_detail).filter_by(order_id=order_id, book_id=store1.book_id).first()
            store1.stock_level += cursor.count

            self.session.add(store1)
            self.session.commit()
            self.session.close()
        except SQLAlchemyError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, 'ok'

    # 搜索图书
    def search(self, buyer_id: str, store_id: str, search_type: str, search_scope: str, search_content: str):
        try:
            # 判断买家id是否存在
            if not self.user_id_exist(buyer_id):
                return error.error_non_exist_user_id(buyer_id)
            # 查找的类型
            type=[book.title,book.tags,book.book_intro,book.content]

            # 全站搜索
            if search_scope == "all":
                # 使用like进行搜索匹配
                all_book = self.session.query(book).filter(type[int(search_type)].like("%" + search_content + "%")).all()

                # 查不到书
                if all_book is None:
                    return error.error_cannot_find_book(buyer_id)

                # 添加查找信息
                book_info = []
                for row in all_book:
                    book_info.append({"title": row.title, "author": row.author, "publisher": row.publisher,
                                      "original_title": row.original_title, "translator": row.translator,
                                      "pub_year": row.pub_year, "pages": row.pages, "price": row.price,
                                      "binding": row.binding, "isbn": row.isbn, "author_Intro": row.author_intro,
                                      "book_intro": row.book_intro, "content": row.content, "tags": row.tags})
            # 当前店铺搜素
            else:
                # 店铺不存在
                if not self.store_id_exist(store_id):
                    return error.error_exist_store_id(store_id)

                store_book = self.session.query(book).join(store, store.book_id == book.id).filter(
                    type[int(search_type)].like("%" + search_content + "%")).all()

                if store_book is None:
                    return error.error_cannot_find_book(buyer_id)

                book_info = []
                for row in store_book:
                    book_info.append({"title": row.title, "author": row.author, "publisher": row.publisher,
                                      "original_title": row.original_title, "translator": row.translator,
                                      "pub_year": row.pub_year, "pages": row.pages, "price": row.price,
                                      "binding": row.binding, "isbn": row.isbn, "author_Intro": row.author_intro,
                                      "book_intro": row.book_intro, "content": row.content, "tags": row.tags})

        except SQLAlchemyError as e:
            print("{}".format(str(e)))
            return 528, "{}".format(str(e))
        except BaseException as e:
            print("{}".format(str(e)))
            return 530, "{}".format(str(e))
        return 200, 'ok', book_info

    # 订单超时自动取消
    def timeout_cancel(self, order_id: str):
        try:
            # 设置最大待支付时间
            payTimeLimit = 5
            # 获取当前时间
            time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # 查找待支付订单
            cursor = self.session.query(new_order).filter_by(order_id=order_id, status="ordered").first()

            # 订单已经支付则无法取消
            if cursor is None:
                return error.error_order_paid(order_id)
            # 获取下单时间
            order_time = datetime.strptime(str(cursor.order_time), "%Y-%m-%d %H:%M:%S")
            # 改变格式, 方便后序计算
            time_now = datetime.strptime(str(time_now), "%Y-%m-%d %H:%M:%S")
            # 计算间隔时间
            duration = (time_now - order_time).seconds
            # 如果超时, 则取消订单
            if duration > payTimeLimit:
                cursor.status = "canceled"
                self.session.add(cursor)
                self.session.commit()

            self.session.close()
        except SQLAlchemyError as e:
            print("{}".format(str(e)))
            return 528, "{}".format(str(e))
        except BaseException as e:
            print("{}".format(str(e)))
            return 530, "{}".format(str(e))
        return 200, 'ok'

