from __future__ import unicode_literals
import frappe

# accounts
class CustomerFrozen(frappe.ValidationError): pass
class InvalidAccountCurrency(frappe.ValidationError): pass
class InvalidCurrency(frappe.ValidationError): pass
