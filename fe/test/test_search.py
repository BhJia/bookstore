import pytest
from fe.access.new_seller import register_new_seller
from fe.access.book import Book
from fe.access import book
from fe.access import auth
from fe import conf
import uuid

class TestSearch:
    @pytest.fixture(autouse=True)
    def pre_run_initialization(self):
        self.auth = auth.Auth(conf.URL)
        self.author = "test_author_{}".format(str(uuid.uuid1()))
        self.book_intro = "test_book_intro_{}".format(str(uuid.uuid1()))
        self.title = "test_title_{}".format(str(uuid.uuid1()))
        self.store_id = "test_store_id_{}".format(str(uuid.uuid1()))

        yield

    def test_search(self):
        assert self.auth.search_author("三毛", "1") == 200
        assert self.auth.search_book_intro("三毛", "2") == 200
        assert self.auth.search_title("三毛", "1") == 200
        assert self.auth.search_author_in_store("三毛", self.store_id,"2") == 200
        assert self.auth.search_book_intro_in_store("三毛", self.store_id,"1") == 200
        assert self.auth.search_title_in_store("三毛", self.store_id,"2") == 200

