# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
def execute():
	from webnotes.utils.nestedset import rebuild_tree

	rebuild_tree("Item Group", "parent_item_group")
	rebuild_tree("Customer Group", "parent_customer_group")
	rebuild_tree("Territory", "parent_territory")
	rebuild_tree("Sales Person", "parent_sales_person")