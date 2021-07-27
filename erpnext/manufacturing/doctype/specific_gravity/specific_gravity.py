# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class SpecificGravity(Document):
	def before_insert(self):
		self.get_details()
	
	def before_submit(self):
		self.make_stock_reconciliation()

	def get_details(self):
		doc=frappe.get_doc("Stock Entry",{"work_order":self.work_order,"stock_entry_type":"Manufacture"})
		lst=frappe.get_doc("Work Order",self.work_order)
		for i in doc.items:
			if i.is_finished_item==1:
				self.append('adjust_density', {
						"batch":i.batch_no,
						"old_specific_gravity":lst.specific_gravity,
						"new_specific_gravity":lst.specific_gravity,
						"old_quantity":lst.qty,
						"new_quantity":lst.qty,
						"old_weight":lst.planned_total_weight,
						"new_weight":lst.planned_total_weight,
						"mo_weight":lst.actual_fg_weight,
						"mo_volume":lst.wo_actual_volume
				})


	#New Quantity
	@frappe.whitelist()
	def change_quant_on_specific_gravity(self):
		lst=frappe.get_doc("Work Order",self.work_order)
		for i in self.adjust_density:
			if lst.actual_fg_weight:
				i.new_weight = i.new_specific_gravity * i.mo_volume
				if i.old_weight > 0.0:
					i.new_quantity = i.new_weight/ i.mo_weight
	
	#New Specific Gravity
	@frappe.whitelist()
	def change_spec_grav_on_quant(self):
		lst=frappe.get_doc("Work Order",self.work_order)
		for i in self.adjust_density:
			if lst.actual_fg_weight:
				i.new_weight = i.new_quantity * i.mo_weight
				if i.mo_volume > 0:
						i.new_specific_gravity = i.new_weight / i.mo_volume

	#New Weight New Volume
	@frappe.whitelist()
	def get_specfic_gravity(self):
		for i in self.adjust_density:
			if self.work_order:
				if i.mo_weight > 0.0:
					i.new_quantity = i.new_weight /i.mo_weight
					if i.mo_volume > 0:
						i.new_specific_gravity = i.new_weight/i.mo_volume


	def make_stock_reconciliation(self):
		for i in self.adjust_density:
			lst=frappe.get_doc("Work Order",self.work_order)
			doc=frappe.new_doc("Stock Reconciliation")
			doc.purpose="Stock Reconciliation"
			doc.append("items", {
			"item_code": lst.production_item,
			# "item_name": wo_doc.item_name
			"warehouse": lst.fg_warehouse,
			"batch_no":i.batch,
			"qty":i.new_quantity
			})
			doc.save(ignore_permissions=True)
			doc.submit()
