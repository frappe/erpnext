# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import money_in_words
from frappe.utils import cint, flt, cstr
from frappe.utils.background_jobs import enqueue


class FeeSchedule(Document):
	def onload(self):
		info = self.get_dashboard_info()
		self.set_onload('dashboard_info', info)

	def get_dashboard_info(self):
		total_unpaid = frappe.db.sql("""select sum(outstanding_amount) from tabFees
			where fee_schedule=%s""", (self.name))
		total_unpaid_amount = flt(total_unpaid[0][0]) if total_unpaid else 0
		info = {}
		info["total_paid"] = self.grand_total - total_unpaid_amount
		info["total_unpaid"] = total_unpaid_amount
		info["currency"] = frappe.defaults.get_defaults().currency
		return info

	def validate(self):
		self.calculate_total()

	def calculate_total(self):
		no_of_students = 0
		for d in self.student_groups:
			# if not d.total_students:
			d.total_students = get_total_students(d.student_group, self.student_category)
			no_of_students += cint(d.total_students)
		self.grand_total = no_of_students*self.total_amount
		self.grand_total_in_words = money_in_words(self.grand_total)

	def create_fees(self):
		if not self.fee_creation_status or self.fee_creation_status == "Failed":
			self.fee_creation_status = "In Process"
			enqueue(generate_fee, queue='default', timeout=6000, event='generate_fee',
				fee_schedule=self.name)
			frappe.msgprint(_("Fee records will be created in the background. In case of any error, the error message will be updated in the Schedule, check after refresh in 5 minutes."))


def generate_fee(fee_schedule):
	doc = frappe.get_doc("Fee Schedule", fee_schedule)
	error = False
	for d in doc.student_groups:
		try:
			students = frappe.db.sql(""" select sg.program, sg.batch, sgs.student, sgs.student_name
				from `tabStudent Group` sg, `tabStudent Group Student` sgs
				where sg.name=%s and sg.name=sgs.parent and sgs.active=1""", d.student_group, as_dict=1)

			# students = frappe.get_all("Student Group Student", fields=["student", "student_name"],
			# 	filters={"parent": d.student_group, "parenttype": "Student Group", "active": 1})
			for student in students:
				doc = get_mapped_doc("Fee Schedule", fee_schedule,	{
					"Fee Schedule": {
						"doctype": "Fees",
						"field_map": {
							"name": "Fee Schedule"
						}
					}
				})
				doc.student = student.student
				doc.student_name = student.student_name
				doc.program = student.program
				doc.student_batch = student.batch
				doc.send_payment_request = 1
				doc.save()
				doc.submit()
		except Exception as e:
			error = True
			err_msg = frappe.local.message_log and "\n\n".join(frappe.local.message_log) or cstr(e)

	if error:
		frappe.db.rollback()
		frappe.db.set_value("Fee Schedule", fee_schedule, "fee_creation_status", "Failed")
		frappe.db.set_value("Fee Schedule", fee_schedule, "error_log", err_msg)

	else:
		frappe.db.set_value("Fee Schedule", fee_schedule, "fee_creation_status", "Successful")
		frappe.db.set_value("Fee Schedule", fee_schedule, "error_log", None)


@frappe.whitelist()
def get_fee_structure(source_name,target_doc=None):
	fee_request = get_mapped_doc("Fee Structure", source_name,
		{"Fee Structure": {
			"doctype": "Fee Schedule"
		}}, ignore_permissions=True)
	return fee_request

@frappe.whitelist()
def get_total_students(student_group, student_category=None):
	conditions = ""
	if student_category:
		conditions = " and s.student_category='{}'".format(frappe.db.escape(student_category))

	return frappe.db.sql("""
		select count(s.name)
		from `tabStudent` s, `tabStudent Group Student` sgs
		where 
			s.name = sgs.student
			and sgs.parent = %s
			and sgs.active = 1
			{conditions}
	""".format(conditions=conditions), student_group)[0][0]
