# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
from frappe.permissions import reset_perms

def execute():
	for doctype in ("About Us Settings", "Accounts Settings", "Activity Type",
		"Blog Category", "Blog Settings", "Blogger", "Branch", "Brand", "Buying Settings",
		"Communication", "Company", "Contact Us Settings",
		"Country", "Currency", "Currency Exchange", "Deduction Type", "Department",
		"Designation", "Earning Type", "Event", "Feed", "File", "Fiscal Year",
		"HR Settings", "Industry Type", "Leave Type", "Letter Head",
		"Mode of Payment", "Module Def", "Naming Series", "POS Setting", "Print Heading",
		"Report", "Role", "Selling Settings", "Stock Settings", "Supplier Type", "UOM"):
		try:
			reset_perms(doctype)
		except:
			print "Error resetting perms for", doctype
			raise
