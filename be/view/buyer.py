from flask import Blueprint
from flask import request
from flask import jsonify
from be.model.buyer import Buyer
from sqlalchemy import Column

bp_buyer = Blueprint("buyer", __name__, url_prefix="/buyer")


@bp_buyer.route("/new_order", methods=["POST"])
def new_order():
    user_id: str = request.json.get("user_id")
    store_id: str = request.json.get("store_id")
    books: [] = request.json.get("books")
    id_and_count = []
    for book in books:
        book_id = book.get("id")
        count = book.get("count")
        id_and_count.append((book_id, count))

    b = Buyer()
    code, message, order_id = b.new_order(user_id, store_id, id_and_count)
    return jsonify({"message": message, "order_id": order_id}), code


@bp_buyer.route("/payment", methods=["POST"])
def payment():
    user_id: str = request.json.get("user_id")
    order_id: str = request.json.get("order_id")
    password: str = request.json.get("password")
    b = Buyer()
    code, message = b.payment(user_id, password, order_id)
    return jsonify({"message": message}), code


@bp_buyer.route("/add_funds", methods=["POST"])
def add_funds():
    user_id = request.json.get("user_id")
    password = request.json.get("password")
    add_value = request.json.get("add_value")
    b = Buyer()
    code, message = b.add_funds(user_id, password, add_value)
    return jsonify({"message": message}), code


# 收货
@bp_buyer.route("/receive_order", methods=["POST"])
def receive_order():
    user_id: str = request.json.get("user_id")
    order_id: str = request.json.get("order_id")
    b = Buyer()
    code, message = b.receive_order(user_id, order_id)
    return jsonify({"message": message}), code


@bp_buyer.route("/cancel_order", methods=["POST"])
def cancel_order():
    buyer_id: str = request.json.get("buyer_id")
    order_id: str = request.json.get("order_id")
    b = Buyer()
    code, message = b.cancel_order(buyer_id, order_id)
    return jsonify({"message": message}), code


@bp_buyer.route("/history_order", methods=["POST"])
def history_order():
    buyer_id: str = request.json.get("buyer_id")
    status: str = request.json.get("status")
    b = Buyer()
    code, message, info = b.history_order(buyer_id, status)
    return jsonify({"message": message, "history info": info}), code


@bp_buyer.route("/timeout_cancel", methods=["POST"])
def timeout_cancel():
    order_id: str = request.json.get("order_id")
    b = Buyer()
    code, message = b.timeout_cancel(order_id)
    return jsonify({"message": message}), code


@bp_buyer.route("/search", methods=["POST"])
def search():
    buyer_id: str = request.json.get("buyer_id")
    store_id: str = request.json.get("store_id")
    search_type: str = request.json.get("search_type")
    search_scope: str = request.json.get("search_scope")
    search_content: str = request.json.get("search_content")
    b = Buyer()
    code, message, info = b.search(buyer_id, store_id, search_type, search_scope, search_content)
    return jsonify({"message": message, "book_info": info}), code
