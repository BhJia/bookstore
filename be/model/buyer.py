####load
import sqlite3 as sqlite
import uuid
import json
import logging
import time
from be.model import db_conn
from be.model import error
from sqlalchemy.exc import SQLAlchemyError
from be.model.postgresql import book, user, user_store, store, new_order, new_order_detail
from sqlalchemy.sql import and_
import datetime

#======如果不运行自动取消订单，请注释掉以下部分
#import redis #为了实现自动删除超时订单
#连接redis数据库
#r=redis.StrictRedis(host='localhost',port=6379,db=0,decode_responses=True)



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

            # 更新订单表数据
            time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # 当前下单时间
            cursor = self.session.query(new_order).filter(new_order.order_id == order_id)
            if cursor == None:
                return error.error_invalid_order_id(order_id)
            cursor.status="paid"
            cursor.pay_time=time
            self.session.add(cursor)

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

    def receive(self, user_id: str, order_id: str):
        try:
            # 判断该用户是否存在
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id) + (order_id,)
            print("用户存在")
            # 判断该订单是否存在在未收货里面
            row = self.session.query(new_order).filter_by(status="delivered" , order_id=order_id)
            order = row.first()
            print("未收货订单", order)
            if order is None:
                return error.error_invalid_order_id(order_id)

            buyer_id = order.user_id
            # 判断该用户是否有这个订单。。。。验证收货的人是否正确
            if user_id != buyer_id:
                return error.error_authorization_fail()

            # 有该订单，收货
            # 添加收货时间
            #timenow = datetime.now().strftime("%Y-%m-%d %H:%M:%S") 不需要打印收货时间，可以省略
            print("******已收货")
            #row.update({new_order.receive_time: timenow})
            self.session.commit()

        except sqlite.Error as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    # 买家查询
    # 比较索引 和模糊查询的 检索效率

    def search_history_status(self, buyer_id: str, flag: int):
        try:
            #检查用户是否存在
            if not self.user_id_exist(buyer_id):
                # print('********')
                code, mes = error.error_non_exist_user_id(buyer_id)
                return code, mes, " "
            # 查所有订单
            if flag == 0:
                record_listn = self.session.query(new_order_detail).filter(new_order_detail.buyer_id == buyer_id)
                print(record_listn)
                records = []
                for record in record_listn:
                    records.append({
                        "order_id": record.order_id,
                        "book_id": record.book_id,
                        "count": record.count,
                        "price": record.price
                    })
                self.session.close()
                # 未付款

            if flag == 1:
                record_list1 = self.session.query(new_order).filter(new_order.status == "ordered",new_order.user_id == buyer_id,
                                                                           new_order.order_time != None)
                print(record_list1)
                records = []
                for record in record_list1:
                    record_infos = self.session.query(new_order_detail).filter_by(order_id=record.order_id).all()
                    records.append({
                        "order_id": record.order_id,
                        #"buyer_id": record.buyer_id,
                        #"store_id": record.store_id,
                        "order_time": record.order_time,
                        "status": '未付款',
                        "book_list": [
                            {"book_id": rei.book_id, "count": rei.count, "price": rei.price}
                            for rei in record_infos
                        ]
                    })
                self.session.close()
                # 已付款待发货
            if flag == 2:
                record_list = self.session.query(new_order).filter(new_order.status == "paid",
                    new_order.user_id == buyer_id, new_order.pay_time != None)
                print(record_list)
                records = []
                for record in record_list:
                    record_infos = self.session.query(new_order_detail).filter_by(order_id=record.order_id).all()
                    records.append({
                        "order_id": record.order_id,
                        #"buyer_id": record.buyer_id,
                        #"store_id": record.store_id,
                        "pay_time": record.pay_time,
                        "status": '已付款待发货',
                        "book_list": [
                            {"book_id": rei.book_id, "count": rei.count, "price": rei.price}
                            for rei in record_infos
                        ]
                    })
                self.session.close()
            # 已发货待收货
            if flag == 3:
                record_list2 = self.session.query(new_order).filter(new_order.status == "delivered" ,
                    new_order.user_id == buyer_id)
                print(record_list2)
                records = []
                for record in record_list2:
                    record_infos = self.session.query(new_order_detail).filter_by(order_id=record.order_id).all()
                    records.append({
                        "order_id": record.order_id,
                        #"buyer_id": record.buyer_id,
                        #"store_id": record.store_id,
                        #"purchase_time": record.purchase_time,
                        "status": '已发货待收货',
                        "book_list": [
                            {"book_id": rei.book_id, "count": rei.count, "price": rei.price}
                            for rei in record_infos
                        ]
                    })
                self.session.close()
            # 已收货
            if flag == 4:
                record_list3 = self.session.query(new_order).filter(new_order.status == "received" ,
                    new_order.user_id == buyer_id)
                print(record_list3)
                records = []
                for record in record_list3:
                    record_infos = self.session.query(new_order_detail).filter_by(order_id=record.order_id).all()
                    records.append({
                        "order_id": record.order_id,
                        #"buyer_id": record.buyer_id,
                        #"store_id": record.store_id,
                        #"receive_time": record.receive_time,
                        "status": '已收货',
                        "book_list": [
                            {"book_id": rei.book_id, "count": rei.count, "price": rei.price}
                            for rei in record_infos
                        ]
                    })
                self.session.close()
            if flag == 5:
                record_list4 = self.session.query(new_order).filter(new_order.status == "canceled",new_order.user_id == buyer_id,
                                                                             new_order.cancel_time != None)
                print(record_list4)
                records = []
                for record in record_list4:
                    record_infos = self.session.query(new_order_detail).filter_by(order_id=record.order_id).all()
                    records.append({
                        "order_id": record.order_id,
                        #"buyer_id": record.buyer_id,
                        #"store_id": record.store_id,
                        #"cancel_time": record.cancel_time,
                        "status": '已取消',
                        "book_list": [
                            {"book_id": rei.book_id, "count": rei.count, "price": rei.price}
                            for rei in record_infos
                        ]
                    })
                self.session.close()
        except BaseException as e:
            return 530, "{}".format(str(e)), []
        return 200, "ok", records

    def cancel(self, buyer_id: str, order_id: str):
        if not self.user_id_exist(buyer_id):
            code,mes =error.error_non_exist_user_id(buyer_id)
            return code ,mes
        #是否属于未付款订单
        store=self.session.query(new_order).filter(new_order.status == "ordered", new_order.user_id == buyer_id , new_order.order_id == order_id,
                                                   new_order.order_time != None).first()
        if store == None:
            # 是否属于已付款且未发货订单
            order1 = self.session.query(new_order).filter(new_order.status == "paid", new_order.order_id == order_id,
                                                          new_order.pay_time != None).first()
            if order1 == None:
                return error.error_invalid_order_id(order_id)
            else:
                store_id = order1.store_id
                price = order1.price

                # 修改订单状态
                order1.status = "canceled"
                ## 卖家减钱
                # 查询卖家
                userstore = self.session.query(user_store).filter(user_store.store_id == store_id).first()

                cursor = self.session.query(user).filter_by(user_id=userstore.user_id)
                if cursor == None:
                    return error.error_not_sufficient_funds(order_id)
                cursor.balance -= price
                self.session.add(cursor)

                ##买家增钱
                cursor = self.session.query(user).filter_by(user_id=buyer_id)
                if cursor == None:
                    return error.error_not_sufficient_funds(order_id)
                cursor.balance += price
                self.session.add(cursor)

                self.session.commit()

        else:
            store_id = store.store_id
            price = store.price
            store.status = "canceled"


        cancel_order = new_order(order_id=order_id , user_id=buyer_id,store_id=store_id,  price=price,status = "canceled")
        if cancel_order == None:
            return error.error_not_sufficient_funds(order_id)
        self.session.add(cancel_order)
        self.session.commit()

        #加库存


    #def test_auto_cancel(self, order_id: str):


    # EXPLAIN ANALYZE SELECT DISTINCT book_id FROM search_book_intro  WHERE tsv_column @@ '美丽' LIMIT 100
    #def search_functions_limit(self, store_id: str, search_type: str, search_input: str, field: str) -> (int, [dict]):
