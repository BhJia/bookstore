import pytest
from fe.access.new_buyer import register_new_buyer
from fe.test.gen_book_data import GenBook
from fe.access.book import Book
import uuid


class TestReceiveOrder:
    @pytest.fixture(autouse=True)
    def pre_run_initialization(self):
        # 参考test_payment
        self.seller_id = "test_payment_seller_id_{}".format(str(uuid.uuid1()))
        self.store_id = "test_payment_store_id_{}".format(str(uuid.uuid1()))
        self.buyer_id = "test_payment_buyer_id_{}".format(str(uuid.uuid1()))
        self.password = self.seller_id
        gen_book = GenBook(self.seller_id, self.store_id)
        ok, buy_book_id_list = gen_book.gen(non_exist_book_id=False, low_stock_level=False, max_book_count=5)
        self.buy_book_info_list = gen_book.buy_book_info_list
        assert ok
        self.seller = gen_book.seller
        b = register_new_buyer(self.buyer_id, self.password)
        self.buyer = b
        code, self.order_id = b.new_order(self.store_id, buy_book_id_list)
        assert code == 200
        self.total_price = 0
        for item in self.buy_book_info_list:
            book: Book = item[0]
            num = item[1]
            if book.price is None:
                continue
            else:
                self.total_price = self.total_price + book.price * num
        yield

    def test_ok(self):
        code = self.buyer.add_funds(self.total_price)
        assert code == 200
        code = self.buyer.payment(self.order_id)
        assert code == 200
        code = self.seller.deliver_order(self.seller_id, self.order_id)
        assert code == 200
        # 收货
        code = self.buyer.receive_order(self.buyer_id,self.order_id)
        assert code == 200

    def test_authorization_error(self):
        code = self.buyer.add_funds(self.total_price)
        assert code == 200
        code = self.buyer.payment(self.order_id)
        assert code == 200
        code = self.seller.deliver_order(self.seller_id, self.order_id)
        assert code == 200
        # 确认收货人身份, 所以需要对买家id进行修改以判断是否正确
        self.buyer_id = self.buyer_id + "_x"
        code = self.buyer.receive_order(self.buyer_id,self.order_id)
        assert code != 200

    def test_order_error(self):
        code = self.buyer.add_funds(self.total_price)
        assert code == 200
        code = self.buyer.payment(self.order_id)
        assert code == 200
        code = self.seller.deliver_order(self.seller_id, self.order_id)
        assert code == 200
        # 确认订单id,对订单id进行修改以判断是否正确
        self.order_id = self.order_id + "_x"
        code = self.buyer.receive_order(self.buyer_id,self.order_id)
        assert code != 200