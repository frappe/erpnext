# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from erpnext.accounts.report.sales_items_to_be_billed.sales_items_to_be_billed import ItemsToBeBilled


def execute(filters=None):
	return ItemsToBeBilled(filters).run("Supplier")
