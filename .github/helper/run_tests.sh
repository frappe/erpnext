#!/bin/bash

cd ~/frappe-bench/ || exit


if [ "$TYPE" == "server" ]; then
  bench --site test_site run-tests --app erpnext --coverage
fi

if [ "$TYPE" == "patch" ]; then
  wget http://build.erpnext.com/20171108_190013_955977f8_database.sql.gz
  bench --site test_site --force restore ~/frappe-bench/20171108_190013_955977f8_database.sql.gz
  bench --site test_site migrate
fi
