# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class BulkStatementOfAccounts(Document):
	pass

@frappe.whitelist()
def get_customer_list(customer_collection, collection_name):
	if customer_collection == 'Customer Group':
		return frappe.get_list('Customer', filter={'customer_group': collection_name}, fields=['name'])
	else:
		return 0