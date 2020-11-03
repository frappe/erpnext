# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from erpnext.stock.stock_ledger import repost_future_sle
from erpnext.accounts.utils import update_gl_entries_after

class RepostItemValuation(Document):
	def validate(self):
		self.set_status()

		if self.based_on == 'Transaction':
			self.item_code = None
			self.warehouse = None
		else:
			self.voucher_type = None
			self.voucher_no = None
	
	def set_status(self, status=None):
		if not status:
			status = 'Queued'
		self.db_set('status', status)

	def on_submit(self):
		frappe.enqueue(repost, timeout=1800, queue='long',
			job_name='repost_sle', now=frappe.flags.in_test, doc=self)

def repost(doc):
	try:
		print("in progress")
		doc.set_status('In Progress')
		repost_sl_entries(doc)
		repost_gl_entries(doc)
		doc.set_status('Completed')
		frappe.db.commit()
	except Exception:
		print("failed")
		frappe.db.rollback()
		traceback = frappe.get_traceback()
		print(traceback)
		frappe.log_error(traceback)
		frappe.db.set_value(doc.doctype, doc.name, 'error_log', traceback)
		doc.set_status('Failed')

def repost_sl_entries(doc):
	if doc.based_on == 'Transaction':
		repost_future_sle(voucher_type=doc.voucher_type, voucher_no=doc.voucher_no,
			allow_negative_stock=doc.allow_negative_stock, via_landed_cost_voucher=doc.via_landed_cost_voucher)
	else:
		repost_future_sle(args=[{
			"item_code": doc.item_code,
			"warehouse": doc.warehouse,
			"posting_date": doc.posting_date,
			"posting_time": doc.posting_time
		}], allow_negative_stock=doc.allow_negative_stock, via_landed_cost_voucher=doc.via_landed_cost_voucher)

def repost_gl_entries(doc):
	if doc.based_on == 'Transaction':
		ref_doc = frappe.get_doc(doc.voucher_type, doc.voucher_no)
		items, warehouses = ref_doc.get_items_and_warehouses()
	else:
		items = [doc.item_code]
		warehouses = [doc.warehouse]

	update_gl_entries_after(doc.posting_date, doc.posting_time,
		warehouses, items, company=doc.company)