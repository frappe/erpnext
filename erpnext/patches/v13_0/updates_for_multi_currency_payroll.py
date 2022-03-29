# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.model.utils.rename_field import rename_field


def execute():

	frappe.reload_doc("Accounts", "doctype", "Salary Component Account")
	if frappe.db.has_column("Salary Component Account", "default_account"):
		rename_field("Salary Component Account", "default_account", "account")

	doctype_list = [
		{"module": "HR", "doctype": "Employee Advance"},
		{"module": "HR", "doctype": "Leave Encashment"},
		{"module": "Payroll", "doctype": "Additional Salary"},
		{"module": "Payroll", "doctype": "Employee Benefit Application"},
		{"module": "Payroll", "doctype": "Employee Benefit Claim"},
		{"module": "Payroll", "doctype": "Employee Incentive"},
		{"module": "Payroll", "doctype": "Employee Tax Exemption Declaration"},
		{"module": "Payroll", "doctype": "Employee Tax Exemption Proof Submission"},
		{"module": "Payroll", "doctype": "Income Tax Slab"},
		{"module": "Payroll", "doctype": "Payroll Entry"},
		{"module": "Payroll", "doctype": "Retention Bonus"},
		{"module": "Payroll", "doctype": "Salary Structure"},
		{"module": "Payroll", "doctype": "Salary Structure Assignment"},
		{"module": "Payroll", "doctype": "Salary Slip"},
	]

	for item in doctype_list:
		frappe.reload_doc(item["module"], "doctype", item["doctype"])

	# update company in employee advance based on employee company
	for dt in [
		"Employee Incentive",
		"Leave Encashment",
		"Employee Benefit Application",
		"Employee Benefit Claim",
	]:
		frappe.db.sql(
			"""
			update `tab{doctype}`
			set company = (select company from tabEmployee where name=`tab{doctype}`.employee)
		""".format(
				doctype=dt
			)
		)

	# update exchange rate for employee advance
	frappe.db.sql("update `tabEmployee Advance` set exchange_rate=1")

	# get all companies and it's currency
	all_companies = frappe.db.get_all(
		"Company", fields=["name", "default_currency", "default_payroll_payable_account"]
	)
	for d in all_companies:
		company = d.name
		company_currency = d.default_currency
		default_payroll_payable_account = d.default_payroll_payable_account

		if not default_payroll_payable_account:
			default_payroll_payable_account = frappe.db.get_value(
				"Account",
				{
					"account_name": _("Payroll Payable"),
					"company": company,
					"account_currency": company_currency,
					"is_group": 0,
				},
			)

		# update currency in following doctypes based on company currency
		doctypes_for_currency = [
			"Employee Advance",
			"Leave Encashment",
			"Employee Benefit Application",
			"Employee Benefit Claim",
			"Employee Incentive",
			"Additional Salary",
			"Employee Tax Exemption Declaration",
			"Employee Tax Exemption Proof Submission",
			"Income Tax Slab",
			"Retention Bonus",
			"Salary Structure",
		]

		for dt in doctypes_for_currency:
			frappe.db.sql(
				"""update `tab{doctype}` set currency = %s where company=%s""".format(doctype=dt),
				(company_currency, company),
			)

		# update fields in payroll entry
		frappe.db.sql(
			"""
			update `tabPayroll Entry`
			set currency = %s,
				exchange_rate = 1,
				payroll_payable_account=%s
			where company=%s
		""",
			(company_currency, default_payroll_payable_account, company),
		)

		# update fields in Salary Structure Assignment
		frappe.db.sql(
			"""
			update `tabSalary Structure Assignment`
			set currency = %s,
				payroll_payable_account=%s
			where company=%s
		""",
			(company_currency, default_payroll_payable_account, company),
		)

		# update fields in Salary Slip
		frappe.db.sql(
			"""
			update `tabSalary Slip`
			set currency = %s,
				exchange_rate = 1,
				base_hour_rate = hour_rate,
				base_gross_pay = gross_pay,
				base_total_deduction = total_deduction,
				base_net_pay = net_pay,
				base_rounded_total = rounded_total,
				base_total_in_words = total_in_words
			where company=%s
		""",
			(company_currency, company),
		)
