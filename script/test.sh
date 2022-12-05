#!/bin/sh
export PATHONPATH=`pwd`
coverage run --timid --branch --source fe,be --concurrency=thread -m pytest -v --ignore=fe/data
coverage combine
coverage report
coverage html

# test_bench 卡住
# test_new_order 1 failed
# test_payment   4 errors

