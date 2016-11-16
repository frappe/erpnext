from __future__ import unicode_literals

import frappe

'''
Some components do not have type set, try and guess whether they turn up in
earnings or deductions in existing salary slips
'''

def execute():
	for s in frappe.db.sql('select name from `tabSalary Component` where ifnull(type, "")=""'):
		compontent = frappe.get_doc('Salary Component', s[0])

		# guess
		guess = frappe.db.sql('''select
			parentfield from `tabSalary Detail`
			where salary_component=%s limit 1''', s[0])

		if guess:
			compontent.type = 'Earning' if guess[0][0]=='earnings' else 'Deduction'

		else:
			compontent.type = 'Deduction'

		compontent.save()