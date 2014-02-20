# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import msgprint, throw, _

class PeriodError(frappe.ValidationError): pass

@frappe.whitelist()
def get_leave_approver_list():
	roles = [r[0] for r in frappe.conn.sql("""select distinct parent from `tabUserRole`
		where role='Leave Approver'""")]
	if not roles:
		msgprint(_("No Leave Approvers. Please assign 'Leave Approver' Role to atleast one user."))

	return roles

@frappe.whitelist()
def get_expense_approver_list():
	roles = [r[0] for r in frappe.conn.sql("""select distinct parent from `tabUserRole`
		where role='Expense Approver'""")]
	if not roles:
		msgprint(_("No Expense Approvers. Please assign 'Expense Approver' Role to atleast one user."))

	return roles

def get_period(from_date, to_date):
	period = frappe.conn.sql_list("""select name from `tabPeriod` 
		where (%s between from_date and to_date) and 
		(%s between from_date and to_date)""", (from_date, to_date))

	if not period:
		throw(_("{msg}: {from_date} to {to_date}").format(**{
			"msg": _("No Period found for date range"),
			"from_date": from_date,
			"to_date": to_date
		}))

	return period

def validate_period(period, from_date, to_date, label="Date"):
	pr = frappe.conn.sql("""select name, from_date, to_date 
		from `tabPeriod` where name=%s and (%s between from_date and to_date) and 
		(%s between from_date and to_date)""", (period, from_date, to_date))

	if not pr:
		throw("From Date: {from_date} and To Date: {to_date} {not}: {period}".format(**{
			"from_date": from_date, 
			"to_date": to_date,
			"not": _("not within Period"),
			"period": period
		}), exc=PeriodError)