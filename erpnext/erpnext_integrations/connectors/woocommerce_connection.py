# see license.txt

from __future__ import unicode_literals
import frappe

@frappe.whitelist(allow_guest=True)
def create_coupon():
	pass

@frappe.whitelist(allow_guest=True)
def update_coupon():
	pass

@frappe.whitelist(allow_guest=True)
def delete_coupon():
	pass

@frappe.whitelist(allow_guest=True)
def restore_coupon():
	pass

@frappe.whitelist(allow_guest=True)
def create_customer():
	pass

@frappe.whitelist(allow_guest=True)
def update_customer():
	pass

@frappe.whitelist(allow_guest=True)
def delete_customer():
	pass

@frappe.whitelist(allow_guest=True)
def create_product():
	pass

@frappe.whitelist(allow_guest=True)
def update_product():
	pass

@frappe.whitelist(allow_guest=True)
def delete_product():
	pass

@frappe.whitelist(allow_guest=True)
def restore_product():
	pass

@frappe.whitelist(allow_guest=True)
def create_order():
	pass

@frappe.whitelist(allow_guest=True)
def update_order():
	pass

@frappe.whitelist(allow_guest=True)
def delete_order():
	pass

@frappe.whitelist(allow_guest=True)
def restore_order():
	pass
