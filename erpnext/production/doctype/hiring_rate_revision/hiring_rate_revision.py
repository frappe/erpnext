# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate, add_days
from frappe import _

class HiringRateRevision(Document):
	def validate(self):
		self.check_duplicates()
		if flt(self.previous_price) <= 0 or flt(self.current_price) <= 0:
			frappe.throw("Either Prevous or Cureent fuel price is Zero")
		self.calculate_variance()
	def on_submit(self):
		self.update_equipment_hiring_form()
	def on_cancel(self):
		self.update_equipment_hiring_form()
	def check_duplicates(self):
		rate = frappe.db.sql('''
				SELECT name FROM `tabHiring Rate Revision` 
				WHERE item_code = '{item_code}' AND fuel_price_list = '{fuel_price_list}'
				AND name != '{name}' AND valid_from <= ifnull('{valid_from}',NOW())
				AND ifnull(valid_upto,NOW()) >= '{valid_from}'
				AND branch = '{branch}' AND equipment_category = '{equipment_category}'
			'''.format(item_code = self.item_code, fuel_price_list = self.fuel_price_list, name = self.name, valid_from = self.valid_from, branch =self.branch, equipment_category = self.equipment_category), as_dict=1)
		if rate:
			msg = ", ".join(frappe.get_desk_link(self.doctype,d.name) for d in rate)
			frappe.throw(
				_(
					"Hiring Rate Revision appears multiple times base on Branch, fuel price list, item and dates.Close following transaction {}".format(frappe.bold(msg))
				),
			)
	def calculate_variance(self):
		self.variance = flt((flt(self.current_price) - flt(self.previous_price))/ flt(self.previous_price)) * 100
		hrs = frappe.get_doc("Hiring Rate Setting")
		if flt(self.variance) <= flt(hrs.lower_range) or flt(self.variance) >= flt(hrs.upper_range) :
			self.rate_applicable = "Applicable"
		else:
			self.rate_applicable = "Not Applicable"


	def update_equipment_hiring_form(self):
		if self.rate_applicable == "Applicable":
			for d in self.items:
				doc = frappe.get_doc("Equipment Hiring Form", d.equipment_hiring_form)
				if self.docstatus == 1:
					# append new row with new rate 
					doc.append("ehf_rate",{
						"reference":self.name,
						"from_date":getdate(self.valid_from),
						"valid_to":getdate(self.valid_upto),
						"hiring_rate": d.revised_rate
					})
				elif self.docstatus == 2:
					# remove row on cancel
					doc.ehf_rate.pop({"name":d.ref_row})
				# update to date in previous row 
				for item in doc.ehf_rate:
					if item.name == d.ref_row and not item.to_date:
						item.to_date = getdate(add_days(self.valid_from, -1)) if self.docstatus == 1 else None
				doc.save()
	@frappe.whitelist()
	def get_hired_equipment(self):
		self.set("items",[])
		for d in frappe.db.sql('''
			select name as equipment_hiring_form, equipment, supplier, start_date, end_date, equipment_category
			from `tabEquipment Hiring Form` where branch = '{branch}' and equipment_category = '{equipment_category}'
			and '{valid_from}' between start_date and end_date
			and fuel_type = '{fuel_type}'
			'''.format(branch = self.branch, equipment_category = self.equipment_category, valid_from = self.valid_from, fuel_type = self.fuel_type), as_dict=1):
			base_rate = frappe.db.sql('''
					select hiring_rate, name from `tabEHF Rate` where parent = '{}' order by idx desc limit 1 
					'''.format(d.equipment_hiring_form))
			row = self.append("items",{})
			if base_rate:
				row.base_rate = base_rate[0][0]
				row.ref_row = base_rate[0][1]
				row.revised_rate = (flt((flt(self.current_price) - flt(self.previous_price))/ flt(self.previous_price),2) * (flt(self.hiring_rate_revision)/100 * flt( base_rate[0][0]))) + flt( base_rate[0][0])
			row.update(d)
@frappe.whitelist()
def filter_fuel_price_list(doctype, txt, searchfield, start, page_len, filters):
	if not filters.get("branch"):
		frappe.throw("Select Branch First")
	
	return frappe.db.sql(
		""" select a.name from `tabFuel Price List` a, `tabCop Branch` b
		where a.name = b.parent and b.branch = %(branch)s and a.name like %(txt)s
		limit %(page_len)s offset %(start)s""",
		{"branch": filters.get("branch"), "start": start, "page_len": page_len, "txt": "%%%s%%" % txt},
	)