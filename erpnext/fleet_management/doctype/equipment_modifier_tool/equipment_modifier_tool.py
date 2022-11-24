# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class EquipmentModifierTool(Document):
	def validate(self):
		self.check_double_entry()
	def on_submit(self):
		self.update_equipment_master()
	def on_cancel(self):
		self.update_equipment_master()
		self.delete_entries()

	def check_double_entry(self):
		found = []
		for eq in self.get("items"):
			if eq.equipment in found:
				frappe.throw("Equipment <b> '{0}' </b> Already Added In The List".format(eq.equipment))
			found.append(eq.equipment)

	
	def update_equipment_master(self):
		for eq in self.get("items"):
			eq_obj = frappe.get_doc("Equipment", eq.equipment)
			if self.docstatus == 1:
				if eq_obj.model_items and  frappe.db.exists("Equipment Model History", {"parent": eq.equipment, \
					"equipment_model": self.new_equipment_model, "equipment_type": self.new_equipment_type, \
					"modified_date": self.posting_date, "equipment_category": self.new_equipment_category}):
					frappe.throw("The Same Record already maintained in Equipment Master <b> '{0}' </b> ".format(eq.equipment))
				else: 
					eq_obj.flags.ignore_permissions = 1,
					eq_obj.db_set("equipment_type", self.new_equipment_type),
					eq_obj.db_set("equipment_model", self.new_equipment_model),
					eq_obj.db_set("equipment_category", self.new_equipment_category),
					eq_obj.append("model_items",{
									"equipment_model": self.new_equipment_model,
									"equipment_type": self.new_equipment_type,
									"modified_date": self.posting_date,
									"equipment_category": self.new_equipment_category,
									"ref_doc": self.name
						})
					eq_obj.save()
			elif self.docstatus == 2 and frappe.db.exists("Equipment Model History",{'parent':eq.equipment,"ref_doc": self.name}):
				eq_obj.flags.ignore_permissions = 1,
				eq_obj.db_set("equipment_type", eq.equipment_type),
				eq_obj.db_set("equipment_model", eq.equipment_model),
				eq_obj.db_set("equipment_category", eq.equipment_category),
				eq_obj.save()

	def delete_entries(self):
		frappe.db.sql("delete from `tabEquipment Model History` where ref_doc = %s", self.name)
