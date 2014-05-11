# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
def execute():
	from webnotes.model.doc import Document
	perms = []
	# create permissions for permlevel 2 assigned to "Credit Days" and "Credit Limit"
	# 2 Accounts Manager r,w
	# 2 System Manager r,w
	perms.append([2, "Accounts Manager", 1, 1, 0, 0])
	perms.append([2, "System Manager", 1, 1, 0, 0])
	perms.append([2, "All", 1, 0, 0, 0])

	# read, write, create, cancel perm for Accounts Manager for permlevel 0
	perms.append([0, "Accounts Manager", 1, 1, 1, 1])

	# permlevel 1 read permission for 'All'
	# 1 All r
	perms.append([1, "All", 1, 0, 0, 0])

	for p in perms:
		d = Document("DocPerm", fielddata={
			"parent": "Customer",
			"parentfield": "permissions",
			"permlevel": p[0],
			"role": p[1],
			"read": p[2],
			"write": p[3],
			"create": p[4],
			"cancel": p[5]
		}).save(1)