# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	# new field address_html is created in place of address field for the company's address
	# patch for moving the address details in the address doc
	company_list = []
	if frappe.db.sql("SHOW COLUMNS FROM `tabCompany` LIKE 'address'"):
		company_list = frappe.db.sql('''select name, address from `tabCompany` where address is not null''', as_dict=1)

	for company in company_list:
		add_list = company.address.split(" ")
		if ',' in company.address:
			add_list = company.address.rpartition(',')
		elif ' ' in company.address:
			add_list = company.address.rpartition(' ')
		else:
			add_list = [company.address, None, company.address]

		doc = frappe.get_doc({
			"doctype":"Address",
			"address_line1": add_list[0],
			"city": add_list[2],
			"is_your_company_address":1,
			"links": [{
				"link_doctype": "Company",
				"link_name": company.name
				}]
			})
		doc.save()
