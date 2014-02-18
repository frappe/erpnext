# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import msgprint, throw, _

class PeriodError(webnotes.ValidationError): pass

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

def get_period(date):
	return webnotes.conn.sql("""select name, from_date, to_date from `tabPeriod` 
		where from_date<=%s and to_date>=%s""", (date, date))[0]

def validate_period(date, period, label="Date"):
	cond = ""
	if period:
		cond = "name = '%s'" % period
	else:
		cond = "'%s' >= from_date and '%s' <= to_date" % (date, date)

	period_list = webnotes.conn.sql("""select name, from_date, to_date 
		from `tabPeriod` where %s""", cond)

	if not period_list:
		throw("{msg}: {date}".format(**{
			"msg": _("Period does not exist for date"), 
			"date": date
		}), exc=PeriodError)
	elif period == period_list:
		throw("{label}: {date} {not}: {period}".format(**{
				"label": label,
				"date": formatdate(date),
				"not": _("not within Period"),
				"period": period
			}))