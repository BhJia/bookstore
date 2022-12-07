import time
import uuid
import pytest

from fe.test.gen_book_data import GenBook
from fe.access.new_buyer import register_new_buyer
from fe.access.book import Book
from be.model.postgresql import book

class Test_search:
    @pytest.fixture(autouse=True)
    def pre_run_initialization(self):
        # 参考test_payment
        self.seller_id = "test_payment_seller_id_{}".format(str(uuid.uuid1()))
        self.store_id = "test_payment_store_id_{}".format(str(uuid.uuid1()))
        self.buyer_id = "test_payment_buyer_id_{}".format(str(uuid.uuid1()))
        self.password = self.seller_id
        gen_book = GenBook(self.seller_id, self.store_id)
        ok, buy_book_id_list = gen_book.gen(non_exist_book_id=False, low_stock_level=False, max_book_count=100)
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
        code=self.buyer.search(self.buyer_id,self.store_id,'0',"all","三毛")
        assert code == 200
        code = self.buyer.search(self.buyer_id, self.store_id, '1', "all", "三毛")
        assert code == 200
        code = self.buyer.search(self.buyer_id, self.store_id, '2', "all", "三毛")
        assert code == 200
        code = self.buyer.search(self.buyer_id, self.store_id,'3', "all", "三毛")
        assert code == 200
        code = self.buyer.search(self.buyer_id, self.store_id, '0', "store", "三毛")
        assert code == 200

    def test_authorization_error(self):
        self.buyer_id=self.buyer_id+ "_x"
        code = self.buyer.search(self.buyer_id, self.store_id, '0', "all", "三毛")
        assert code != 200

    def test_store_error(self):
        self.store_id = self.store_id + "_x"
        code = self.buyer.search(self.buyer_id, self.store_id, '0', "store", "三毛")
        assert code != 200