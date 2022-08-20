# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber, Anthony Emmanuel and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class QuotationComparisonSheet(Document):
	def on_submit(self):
		pass

	@frappe.whitelist()
	def get_rfq(self, rfq):
		return {
			'rfq': frappe.get_doc('Request for Quotation', rfq)
		}

	@frappe.whitelist()
	def create_purchase_order(self, **kwargs):
		# create purchase receipt
		request_for_quotation = frappe.get_doc('Request for Quotation', self.request_for_quotation)
		# sort suppliers
		suppliers = {}
		for i in self.items:
			if(suppliers.get(i.supplier)):
				suppliers[i.supplier].append(i)
			else:
				suppliers[i.supplier] = [i]

		# create purchase order
		for supplier, items in suppliers.items():
			po_items = []
			for i in items:
				po_items.append({
					'item_code': i.item_code,
					'schedule_date': i.schedule_date,
					'qty': i.qty,
					'rate': i.rate,
					'warehouse':i.warehouse,
					'uom': i.uom,
				})
			doc = frappe.get_doc({
				'doctype':'Purchase Order',
				'supplier':supplier,
				'items': po_items,
				'schedule_date': request_for_quotation.schedule_date
			}).insert()
		frappe.msgprint(_('PO creation complete'));
		return



@frappe.whitelist()
def get_quotation_against_rfq(rfq):
	supplier_quotation_list = frappe.db.get_list('Supplier Quotation Item', filters={
		'request_for_quotation': rfq,
		'docstatus':1,
		},
		fields=['parent'],
		group_by="parent",
	)
	quotations = []
	for supplier_quotation in supplier_quotation_list:
		quotations.append(frappe.get_doc('Supplier Quotation', supplier_quotation.parent))
	print(quotations)
	return quotations
