#!/bin/bash

cd ~/
bench init frappe-bench --frappe-path https://github.com/SaiFi0102/frappe.git --frappe-branch master --python $(which python)
