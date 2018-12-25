#!/bin/bash

cd ~/
curl -I https://github.com/surajshetty3416/frappe/tree/$TRAVIS_BRANCH | head -n 1 | cut -d $' ' -f2 | (
	read response;
	[ $response == '200' ] && branch=$TRAVIS_BRANCH || branch='develop';
	bench init frappe-bench --frappe-path https://github.com/surajshetty3416/frappe.git --frappe-branch $branch --python $(which python)
)
