# see license.txt

from __future__ import unicode_literals
import frappe

@frappe.whitelist(allow_guest=True)
def coupon_created():
	pass

@frappe.whitelist(allow_guest=True)
def coupon_updated():
	pass

@frappe.whitelist(allow_guest=True)
def coupon_deleted():
	pass

@frappe.whitelist(allow_guest=True)
def coupon_restored():
	pass
