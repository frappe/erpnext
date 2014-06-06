# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	for doctype in ("About Us Settings", "Accounts Settings", "Activity Type",
		"Blog Category", "Blog Settings", "Blogger", "Branch", "Brand", "Buying Settings",
		"Comment", "Communication", "Company", "Contact Us Settings",
		"Country", "Currency", "Currency Exchange", "Deduction Type", "Department",
		"Designation", "Earning Type", "Event", "Feed", "File Data", "Fiscal Year",
		"HR Settings", "Industry Type", "Jobs Email Settings", "Leave Type", "Letter Head",
		"Mode of Payment", "Module Def", "Naming Series", "POS Setting", "Print Heading",
		"Report", "Role", "Sales Email Settings", "Selling Settings", "Stock Settings", "Supplier Type", "UOM"):
		try:
			frappe.reset_perms(doctype)
		except:
			print "Error resetting perms for", doctype
			raise
