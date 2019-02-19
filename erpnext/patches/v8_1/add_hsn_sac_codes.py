from __future__ import unicode_literals
import frappe
from erpnext.regional.india.setup import setup

def execute():
	company = frappe.get_all('Company', filters = {'country': 'India'})
	if not company:
		return

	# call setup for india
	setup(patch=True)