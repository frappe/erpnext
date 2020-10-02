# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import copy
from frappe.model.document import Document


class TransactionType(Document):
	pass


@frappe.whitelist()
def get_transaction_type_defaults(transaction_type, company):
	if transaction_type:
		tranction_type_doc = frappe.get_cached_doc("Transaction Type", transaction_type)
		if tranction_type_doc:
			for d in tranction_type_doc.item_defaults or []:
				if d.company == company:
					row = copy.deepcopy(d.as_dict())
					row.pop("name")
					return row

	return frappe._dict()
