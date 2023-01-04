# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _, qb, throw, bold
from frappe.utils import flt, cint, nowdate, getdate

class EquipmentHiringForm(Document):
	def validate(self):
		self.validate_date()
		self.check_duplicate()
	def on_update_after_submit(self):
		self.validate_date()
		for a in self.get('efh_extension'):
			if not a.hiring_end_date:
				if a.hiring_extended_till > self.end_date:
					a.hiring_end_date = self.end_date
					frappe.db.sql("update `tabEHF Extension` set hiring_end_date='{}' where name='{}'".format(self.end_date, a.name))
					self.db_set("end_date", a.hiring_extended_till)
				else:
					frappe.throw("Equipment Hiring End date is already after the extension date {}".format(a.hiring_extended_till))

		frappe.db.commit()
	def check_duplicate(self):
		if frappe.db.sql('''
			select 1 from `tabEquipment Hiring Form` where name != '{0}' and ('{1}' between start_date and end_date
			or '{2}' between start_date and end_date)
			and docstatus = 1 
			and equipment ='{3}'
			'''.format(self.name,self.start_date,self.end_date,self.equipment)):
			frappe.throw("Equipment Hiring Form Already exists for Equipment {}".format(self.equipment))
	def validate_date(self):
		if getdate(self.start_date) > getdate(self.end_date):
			frappe.throw("Start Date cannot be greater than End Date")
		for d in self.ehf_rate:
			if getdate(d.from_date) < getdate(self.start_date):
				throw("From Date cannot be greater than Equipment Start Date at row {}".format(bold(d.idx)))
			if getdate(d.to_date) > getdate(self.end_date):
				throw("To Date cannot be greater than Equipment End Date at row {}".format(bold(d.idx)))
			if d.to_date and getdate(d.from_date) > getdate(d.to_date):
				throw("From Date cannot be greater than To Date at row {}".format(bold(d.idx)))

			# validate date verlapping
			n = flt(d.idx)-1
			i = 0
			while i < n:
				if getdate(d.from_date) >= getdate(self.ehf_rate[i].from_date) and getdate(d.from_date) <= getdate(self.ehf_rate[i].to_date):
					throw("From Date at row {} is overlapping with row no {}".format(bold(d.idx),bold(self.ehf_rate[i].idx)))

				if d.to_date and getdate(d.to_date) >= getdate(self.ehf_rate[i].from_date) and getdate(d.to_date) <= getdate(self.ehf_rate[i].to_date):
					throw("To Date at row {} is overlapping with row no {}".format(bold(d.idx),bold(self.ehf_rate[i].idx)))
				i  = i + 1

	def validate_update_after_submit(self):
		efh_extension_count = frappe.db.sql("select count(*) from `tabEHF Extension` where parent = '{}'".format(self.name))
		efh_rate_count = frappe.db.sql("select count(*) from `tabEHF Rate` where parent = '{}'".format(self.name))
		extension_count = rate_count = 0
		for a in self.get('efh_extension'):
			extension_count += 1
		
		if extension_count < efh_extension_count[0][0]:
			frappe.throw("You are not allowed to <b>remove the record in Extension table</b>. Please reload to load the record again")

		for b in self.get('ehf_rate'):
			rate_count += 1
			if not b.name:
				if getdate(b.from_date) > getdate(b.to_date):
					frappe.throw("From Date cannot be after to Date")
				check = frappe.db.sql("""select count(*) 
									from `tabEHF Rate` where ('{}' between from_date and to_date 
									or '{}' between from_date and to_date)
									and parent = '{}'
									""".format(b.from_date, b.to_date, self.name))
				if check[0][0] > 0:
					frappe.throw("Row ID : <b>{} </b>date range {} and {} is already defined.".format(b.idx, b.from_date, b.to_date))

		if rate_count < efh_rate_count[0][0]:
			frappe.throw("You are not allowed to <b>remove the record in Rate table</b>. Please reload to load the record again")
@frappe.whitelist()
def make_logbook(source_name, target_doc=None):
	from frappe.model.mapper import get_mapped_doc

	def post_process(source, target):
		target.reversal_of = source.name

	doclist = get_mapped_doc("Equipment Hiring Form",source_name,{
				"Equipment Hiring Form": {
				"doctype": "Logbook",
				"field_map":{
					"equipment_hiring_form":"name",
				}
			},
		},
		target_doc,
		post_process,
	)

	return doclist