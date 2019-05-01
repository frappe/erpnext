#!/bin/bash

set -e

if [[ $TEST_TYPE == 'Server Side Test' ]]; then
    bench run-tests --app erpnext --coverage

elif [[ $TEST_TYPE == 'Patch Test' ]]; then
    wget http://build.erpnext.com/20171108_190013_955977f8_database.sql.gz
    bench --force restore ~/frappe-bench/20171108_190013_955977f8_database.sql.gz --mariadb-root-password travis
    bench migrate
fi
