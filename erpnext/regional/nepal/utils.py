# Copyright (c) 2018, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from erpnext import get_region

def check_deletion_permission(doc, method):
	region = get_region()
	if region not in ["Nepal"]:
		return
	else:
		frappe.throw(_("Deletion is not permitted for country {0}".format(region)))

# don't remove this function it is used in tests
def test_method():
	'''test function'''
	return 'overridden'
