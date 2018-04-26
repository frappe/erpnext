# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, nowdate, formatdate

def set_employee_name(doc):
	if doc.employee and not doc.employee_name:
		doc.employee_name = frappe.db.get_value("Employee", doc.employee, "employee_name")

def validate_dates(doc, from_date, to_date):
	date_of_joining, relieving_date = frappe.db.get_value("Employee", doc.employee, ["date_of_joining", "relieving_date"])
	if getdate(from_date) > getdate(to_date):
		frappe.throw(_("To date can not be less than from date"))
	elif getdate(from_date) > getdate(nowdate()):
		frappe.throw(_("Future dates not allowed"))
	elif date_of_joining and getdate(from_date) < getdate(date_of_joining):
		frappe.throw(_("From date can not be less than employee's joining date"))
	elif relieving_date and getdate(to_date) > getdate(relieving_date):
		frappe.throw(_("To date can not greater than employee's relieving date"))

def validate_overlap(doc, from_date, to_date, company = None):
	query = """
		select name
		from `tab{0}`
		where name != %(name)s
		"""
	query += get_doc_condition(doc.doctype)

	if not doc.name:
		# hack! if name is null, it could cause problems with !=
		doc.name = "New "+doc.doctype

	overlap_doc = frappe.db.sql(query.format(doc.doctype),{
			"employee": doc.employee,
			"from_date": from_date,
			"to_date": to_date,
			"name": doc.name,
			"company": company
		}, as_dict = 1)

	if overlap_doc:
		exists_for = doc.employee
		if company:
			exists_for = company
		throw_overlap_error(doc, exists_for, overlap_doc[0].name, from_date, to_date)

def get_doc_condition(doctype):
	if doctype == "Compensatory Leave Request":
		return "and employee = %(employee)s and docstatus < 2 \
		and (work_from_date between %(from_date)s and %(to_date)s \
		or work_end_date between %(from_date)s and %(to_date)s \
		or (work_from_date < %(from_date)s and work_end_date > %(to_date)s))"
	elif doctype == "Leave Period":
		return "and company = %(company)s and (from_date between %(from_date)s and %(to_date)s \
			or to_date between %(from_date)s and %(to_date)s \
			or (from_date < %(from_date)s and to_date > %(to_date)s))"

def throw_overlap_error(doc, exists_for, overlap_doc, from_date, to_date):
	msg = _("A {0} exists between {1} and {2} (").format(doc.doctype,
		formatdate(from_date), formatdate(to_date)) \
		+ """ <b><a href="#Form/{0}/{1}">{1}</a></b>""".format(doc.doctype, overlap_doc) \
		+ _(") for {0}").format(exists_for)
	frappe.throw(msg)

def get_employee_leave_policy(employee):
	leave_policy = frappe.db.get_value("Employee", employee, "leave_policy")
	if not leave_policy:
		employee_grade = frappe.db.get_value("Employee", employee, "grade")
		if employee_grade:
			leave_policy = frappe.db.get_value("Employee Grade", employee_grade, "default_leave_policy")
			if not leave_policy:
				frappe.throw(_("Employee {0} of grade {1} have no default leave policy").format(employee, employee_grade))
		else:
			frappe.throw(_("Employee {0} has no grade to get default leave policy").format(employee))
	if leave_policy:
		return frappe.get_doc("Leave Policy", leave_policy)

def get_leave_period(from_date, to_date, company):
	leave_period = frappe.db.sql("""
		select name, from_date, to_date
		from `tabLeave Period`
		where company=%(company)s and is_active=1
			and (from_date between %(from_date)s and %(to_date)s
				or to_date between %(from_date)s and %(to_date)s
				or (from_date < %(from_date)s and to_date > %(to_date)s))
	""", {
		"from_date": from_date,
		"to_date": to_date,
		"company": company
	}, as_dict=1)

	if leave_period:
		return leave_period
	else:
		frappe.throw(_("There is no leave period in between {0} and {1}").format(from_date, to_date))
