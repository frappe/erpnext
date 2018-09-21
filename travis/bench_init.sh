#!/bin/bash

cd ~/
curl -I https://github.com/surajshetty3416/frappe/tree/pg-poc | head -n 1 | cut -d $' ' -f2 | (
	read response;
	[ $response == '200' ] && branch='pg-poc' || branch='develop';
	bench init frappe-bench --frappe-path https://github.com/surajshetty3416/frappe.git --frappe-branch $branch --python $(which python)
)
