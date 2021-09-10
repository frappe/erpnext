from __future__ import unicode_literals

# import frappe
from erpnext.setup.install import add_standard_navbar_items


def execute():
	# Add standard navbar items for ERPNext in Navbar Settings
	add_standard_navbar_items()
