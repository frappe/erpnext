# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import flt, cint
from frappe import _, scrub
from frappe.desk.query_report import group_report_data


def execute(filters=None):
	filters = frappe._dict(filters)
	filters.show_employee_name = frappe.get_cached_value("HR Settings", None, "emp_created_by") != "Full Name"

	salary_slips = get_salary_slips(filters)
	if not salary_slips:
		return [], []

	columns = get_columns(salary_slips, filters)
	ss_earning_map = get_ss_earning_map(salary_slips)
	ss_ded_map = get_ss_ded_map(salary_slips)
	doj_map = get_employee_doj_map()

	data = []

	for ss in salary_slips:
		row = frappe._dict({
			"salary_slip_id": ss.name,
			"employee": ss.employee,
			"employee_name": ss.employee_name,
			"disable_party_name_formatter": cint(filters.show_employee_name),
			"date_of_joining": doj_map.get(ss.employee),
			"branch": ss.branch,
			"department": ss.department,
			"designation": ss.designation,
			"company": ss.company,
			"start_date": ss.start_date,
			"end_date": ss.end_date,
			"late_days": ss.late_days,
			"leave_without_pay": ss.leave_without_pay,
			"payment_days": ss.payment_days,
			"total_working_days": ss.total_working_days,
			"gross_pay": ss.gross_pay,
			"loan_repayment": ss.total_loan_repayment if ss.total_loan_repayment else None,
			"advance_deduction": ss.total_advance_amount if ss.total_advance_amount else None,
			"total_deduction": ss.total_deduction + ss.total_loan_repayment + ss.total_advance_amount,
			"net_pay": ss.net_pay,
			"rounded_total": ss.rounded_total,
			"bank_amount": ss.bank_amount or None,
			"cheque_amount": ss.cheque_amount or None,
			"cash_amount": ss.cash_amount or None,
			"no_mode_amount": ss.no_mode_amount or None,
		})

		if ss.salary_mode == "Bank":
			row['bank_amount_' + scrub(ss.bank_name or 'Unknown Bank')] = ss.bank_amount

		for c in columns:
			if c.get("is_earning"):
				row[c.get("fieldname")] = ss_earning_map.get(ss.name, {}).get(c.get("label"))
			elif c.get("is_deduction"):
				row[c.get("fieldname")] = ss_ded_map.get(ss.name, {}).get(c.get("label"))

		data.append(row)

	grouped_data = get_grouped_data(columns, data, filters)
	return columns, grouped_data


def get_grouped_data(columns, data, filters):
	group_by = [None]
	for i in range(2):
		group_label = filters.get("group_by_" + str(i + 1), "").replace("Group by ", "")

		if not group_label or group_label == "Ungrouped":
			continue
		else:
			group_field = scrub(group_label)
		group_by.append(group_field)

	if len(group_by) <= 1:
		return data

	exclude_columns = ['payment_days', 'total_working_days']
	total_fields = [c['fieldname'] for c in columns if c['fieldtype'] in ['Float', 'Currency', 'Int']
		and c['fieldname'] not in exclude_columns]

	def postprocess_group(group_object, grouped_by):
		if not group_object.group_field:
			group_object.totals['employee'] = "'Total'"
		else:
			group_object.totals['employee'] = "'{0}: {1}'".format(group_object.group_label, group_object.group_value)

	return group_report_data(data, group_by, total_fields=total_fields, postprocess_group=postprocess_group)


def get_columns(salary_slips, filters):
	branch = department = designation = leave_without_pay = late_days = loan_repayment = advance_deduction\
		= no_mode_amount = cash_amount = cheque_amount = False

	period_set = set()
	for ss in salary_slips:
		if ss.get('branch'): branch = True
		if ss.get('department'): department = True
		if ss.get('designation'): designation = True
		if ss.get('late_days'): late_days = True
		if ss.get('leave_without_pay'): leave_without_pay = True
		if ss.get('total_loan_repayment'): loan_repayment = True
		if ss.get('total_advance_amount'): advance_deduction = True
		if ss.get('cheque_amount'): cheque_amount = True
		if ss.get('cash_amount'): cash_amount = True
		if ss.get('no_mode_amount'): no_mode_amount = True

		period_set.add((ss.start_date, ss.end_date))

	columns = [
		{
			"label": _("Salary Slip"), "fieldtype": "Link", "fieldname": "salary_slip_id","options": "Salary Slip",
			"width": 80
		},
		{
			"label": _("Employee"), "fieldtype": "Link", "fieldname": "employee", "options": "Employee",
			"width": 80 if filters.show_employee_name else 140
		},
	]

	if filters.show_employee_name:
		columns.append({
			"label": _("Employee Name"), "fieldtype": "Data", "fieldname": "employee_name", "width": 140
		})

	columns += [
		{
			"label": _("Join Date"), "fieldtype": "Date", "fieldname": "date_of_joining", "width": 80,
			"keep": filters.show_date_of_joining
		},
		{
			"label": _("Branch"), "fieldtype": "Link", "fieldname": "branch", "options": "Branch", "width": 120,
			"keep": branch and filters.show_branch
		},
		{
			"label": _("Department"), "fieldtype": "Link", "fieldname": "department", "options": "Department",
			"width": 100, "keep": department and filters.show_department
		},
		{
			"label": _("Designation"), "fieldtype": "Link", "fieldname": "designation", "options": "Designation",
			"width": 100, "keep": designation and filters.show_designation
		},
		{
			"label": _("Start Date"), "fieldtype": "Date", "fieldname": "start_date", "width": 80,
			"keep": len(period_set) > 1
		},
		{
			"label": _("End Date"), "fieldtype": "Date", "fieldname": "end_date", "width": 80,
			"keep": len(period_set) > 1
		},
		{
			"label": _("Work Days"), "fieldtype": "Float", "fieldname": "total_working_days", "width": 65, "precision": 1,
			"keep": filters.show_working_days
		},
		{
			"label": _("Late Days"), "fieldtype": "Float", "fieldname": "late_days", "width": 65, "precision": 1,
			"keep": late_days
		},
		{
			"label": _("Leave Without Pay"), "fieldtype": "Float", "fieldname": "leave_without_pay", "width": 65, "precision": 1,
			"keep": leave_without_pay
		},
		{
			"label": _("Payment Days"), "fieldtype": "Float", "fieldname": "payment_days", "width": 65, "precision": 1,
		}
	]

	salary_components = {_("Earning"): [], _("Deduction"): []}
	ss_components = frappe.db.sql("""
		select distinct sd.salary_component, sc.type
		from `tabSalary Detail` sd, `tabSalary Component` sc
		where sc.name = sd.salary_component and sd.amount != 0 and sd.parent in ({0})
	""".format(', '.join(['%s']*len(salary_slips))), [d.name for d in salary_slips], as_dict=1)

	for component in ss_components:
		salary_components[_(component.type)].append(component.salary_component)

	for e in salary_components[_("Earning")]:
		columns.append({
			"label": _(e), "fieldtype": "Currency", "fieldname": scrub(e), "is_earning": 1, "width": 90
		})

	columns.append({
		"label": _("Gross Pay"), "fieldtype": "Currency", "fieldname": "gross_pay", "width": 90
	})

	for d in salary_components[_("Deduction")]:
		columns.append({
			"label": _(d), "fieldtype": "Currency", "fieldname": scrub(d), "is_deduction": 1, "width": 90
		})

	columns += [
		{
			"label": _("Loan Repayment"), "fieldtype": "Currency",
			"fieldname": "loan_repayment", "width": 90, "keep": loan_repayment
		},
		{
			"label": _("Advance Deduction"), "fieldtype": "Currency",
			"fieldname": "advance_deduction", "width": 90, "keep": advance_deduction
		},
		{
			"label": _("Total Deduction"), "fieldtype": "Currency",
			"fieldname": "total_deduction", "width": 90
		},
		{
			"label": _("Net Pay"), "fieldtype": "Currency",
			"fieldname": "net_pay", "width": 90
		},
		{
			"label": _("Rounded Total"), "fieldtype": "Currency",
			"fieldname": "rounded_total", "width": 90
		}
	]

	bank_names = [ss.bank_name or 'Unknown Bank' for ss in salary_slips if ss.salary_mode == "Bank"]
	bank_names = list(set(bank_names))

	for bank_name in bank_names:
		columns += [
			{
				"label": _(bank_name + " Amount"), "fieldtype": "Currency",
				"fieldname": 'bank_amount_' + scrub(bank_name), "width": 90
			},
		]

	columns += [
		{
			"label": _("Cheque Amount"), "fieldtype": "Currency",
			"fieldname": "cheque_amount", "width": 90, "keep": cheque_amount
		},
		{
			"label": _("Cash Amount"), "fieldtype": "Currency",
			"fieldname": "cash_amount", "width": 90, "keep": cash_amount
		},
		{
			"label": _("No Salary Mode"), "fieldtype": "Currency",
			"fieldname": "no_mode_amount", "width": 90, "keep": no_mode_amount
		},
	]

	columns = [c for c in columns if c.get('keep', True)]
	return columns


def get_salary_slips(filters):
	filters.update({"from_date": filters.get("from_date"), "to_date":filters.get("to_date")})
	conditions, filters = get_conditions(filters)
	salary_slips = frappe.db.sql("""select * from `tabSalary Slip` where %s
		order by employee, start_date""" % conditions, filters, as_dict=1)

	return salary_slips or []


def get_conditions(filters):
	conditions = ""
	doc_status = {"Draft": 0, "Submitted": 1, "Cancelled": 2}

	if filters.get("docstatus"):
		if filters.get("docstatus") == "Draft and Submitted":
			conditions += "docstatus < 2"
		else:
			conditions += "docstatus = {0}".format(doc_status[filters.get("docstatus")])

	if filters.get("from_date"): conditions += " and start_date >= %(from_date)s"
	if filters.get("to_date"): conditions += " and end_date <= %(to_date)s"
	if filters.get("company"): conditions += " and company = %(company)s"
	if filters.get("employee"): conditions += " and employee = %(employee)s"

	return conditions, filters


def get_employee_doj_map():
	return frappe._dict(frappe.db.sql("""
		SELECT
			employee,
			date_of_joining
		FROM `tabEmployee`
	"""))


def get_ss_earning_map(salary_slips):
	ss_earnings = frappe.db.sql("""select parent, salary_component, amount
		from `tabSalary Detail` where parent in (%s)""" %
		(', '.join(['%s']*len(salary_slips))), tuple([d.name for d in salary_slips]), as_dict=1)

	ss_earning_map = {}
	for d in ss_earnings:
		ss_earning_map.setdefault(d.parent, frappe._dict()).setdefault(d.salary_component, [])
		ss_earning_map[d.parent][d.salary_component] = flt(d.amount)

	return ss_earning_map


def get_ss_ded_map(salary_slips):
	ss_deductions = frappe.db.sql("""select parent, salary_component, amount
		from `tabSalary Detail` where parent in (%s)""" %
		(', '.join(['%s']*len(salary_slips))), tuple([d.name for d in salary_slips]), as_dict=1)

	ss_ded_map = {}
	for d in ss_deductions:
		ss_ded_map.setdefault(d.parent, frappe._dict()).setdefault(d.salary_component, [])
		ss_ded_map[d.parent][d.salary_component] = flt(d.amount)

	return ss_ded_map
