# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
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
		info = {
			"total_paid": 0,
			"total_unpaid": 0,
			"currency": erpnext.get_company_currency(self.company)
		}

		fees_amount = frappe.db.sql("""select sum(grand_total), sum(outstanding_amount) from tabFees
			where fee_schedule=%s and docstatus=1""", (self.name))

		if fees_amount:
			info["total_paid"] = flt(fees_amount[0][0]) - flt(fees_amount[0][1])
			info["total_unpaid"] = flt(fees_amount[0][1])

		return info

	def validate(self):
		self.calculate_total()

	def calculate_total(self):
		no_of_students = 0
		for d in self.student_groups:
			# if not d.total_students:
			d.total_students = get_total_students(d.student_group, self.academic_year,
				self.academic_term, self.student_category)
			no_of_students += cint(d.total_students)
		self.grand_total = no_of_students*self.total_amount
		self.grand_total_in_words = money_in_words(self.grand_total)

	def create_fees(self):
		self.db_set("fee_creation_status", "In Process")
		frappe.publish_realtime("fee_schedule_progress",
			{"progress": "0", "reload": 1}, user=frappe.session.user)
		enqueue(generate_fee, queue='default', timeout=6000, event='generate_fee',
			fee_schedule=self.name)

def generate_fee(fee_schedule):
	doc = frappe.get_doc("Fee Schedule", fee_schedule)
	error = False
	total_records = sum([int(d.total_students) for d in doc.student_groups])
	created_records = 0
	for d in doc.student_groups:
		students = frappe.db.sql(""" select sg.program, sg.batch, sgs.student, sgs.student_name
			from `tabStudent Group` sg, `tabStudent Group Student` sgs
			where sg.name=%s and sg.name=sgs.parent and sgs.active=1""", d.student_group, as_dict=1)

		for student in students:
			try:
				fees_doc = get_mapped_doc("Fee Schedule", fee_schedule,	{
					"Fee Schedule": {
						"doctype": "Fees",
						"field_map": {
							"name": "Fee Schedule"
						}
					}
				})
				fees_doc.student = student.student
				fees_doc.student_name = student.student_name
				fees_doc.program = student.program
				fees_doc.student_batch = student.batch
				fees_doc.send_payment_request = doc.send_email
				fees_doc.save()
				fees_doc.submit()
				created_records += 1
				frappe.publish_realtime("fee_schedule_progress", {"progress": str(int(created_records * 100/total_records))}, user=frappe.session.user)

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

	frappe.publish_realtime("fee_schedule_progress",
		{"progress": "100", "reload": 1}, user=frappe.session.user)


@frappe.whitelist()
def get_fee_structure(source_name,target_doc=None):
	fee_request = get_mapped_doc("Fee Structure", source_name,
		{"Fee Structure": {
			"doctype": "Fee Schedule"
		}}, ignore_permissions=True)
	return fee_request

@frappe.whitelist()
def get_total_students(student_group, academic_year, academic_term=None, student_category=None):
	conditions = ""
	if student_category:
		conditions = " and pe.student_category='{}'".format(frappe.db.escape(student_category))
	if academic_term:
		conditions = " and pe.academic_term='{}'".format(frappe.db.escape(academic_term))


	return frappe.db.sql("""
		select count(pe.name)
		from `tabStudent Group Student` sgs, `tabProgram Enrollment` pe
		where 
			pe.student = sgs.student
			and pe.academic_year = %s
			and sgs.parent = %s
			and sgs.active = 1
			{conditions}
	""".format(conditions=conditions), (academic_year, student_group))[0][0]
