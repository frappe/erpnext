# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class StockLedgerEntryDependency(Document):
	pass


def on_doctype_update():
	frappe.db.add_index("Stock Ledger Entry Dependency", [
		"dependent_voucher_detail_no", "dependent_voucher_type", "dependent_voucher_no"
	], index_name='dependency_key')
