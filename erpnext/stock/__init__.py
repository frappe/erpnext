from __future__ import unicode_literals
install_docs = [
	{"doctype":"Role", "role_name":"Stock Manager", "name":"Stock Manager"},
	{"doctype":"Role", "role_name":"Item Manager", "name":"Item Manager"},
	{"doctype":"Role", "role_name":"Stock User", "name":"Stock User"},
	{"doctype":"Role", "role_name":"Quality Manager", "name":"Quality Manager"},
	{"doctype":"Item Group", "item_group_name":"All Item Groups", "is_group": 1},
	{"doctype":"Item Group", "item_group_name":"Default", 
		"parent_item_group":"All Item Groups", "is_group": 0},
]
