# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate
class EMEInvoiceEntry(Document):
	def validate(self):
		self.check_date()

	def check_date(self):
		if self.from_date > self.to_date:
			frappe.throw("From date cannot be grater than To Date")
	def on_submit(self):
		pass
	@frappe.whitelist()
	def create_eme_invoice(self):
		self.check_permission('write')
		owner_list = self.get_owner_list()
		if owner_list:
			args = frappe._dict({
				"eme_invoice_entry":self.name,
				"branch":self.branch,
				"cost_center":self.cost_center,
				"posting_date":nowdate(),
				"from_date":self.from_date,
				"to_date":self.to_date,
				"tds_percent":self.tds_percent,
				"tds_account":self.tds_account,
				"company":self.company,
				"currency":self.currency
			})
	def get_owner_list(self):
		owner = []
		for item in self.items:
			if item.supplier not in owner:
				owner.append(item.supplier)
		return owner

	@frappe.whitelist()
	def get_supplier_with_equipment(self):
		if self.from_date > self.to_date:
			frappe.throw("From Date cannot be ealier than to Date")
		else:
			data = frappe.db.sql("""
					select supplier, equipment, name as equipment_hiring_form, start_date, end_date
					from 
						`tabEquipment Hiring Form`
					where 
					'{0}' between start_date and end_date
					and '{1}' between start_date and end_date
					and docstatus = 1
					and cost_cebter = '{2}'
			""".format(self.from_date, self.to_date, self.cost_cebter), as_dict=True)
			if data:
				self.set("items",[])
				for x in data:
					row = self.append("items",{})
					row.update(x)
	