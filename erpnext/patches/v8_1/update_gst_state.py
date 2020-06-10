from __future__ import unicode_literals
import frappe
from erpnext.regional.india import states

def execute():
	company = frappe.get_all('Company', filters = {'country': 'India'})
	if not company:
		return

	if not frappe.db.get_value("Custom Field", filters={'fieldname':'gst_state'}):
		return

	frappe.db.sql("update `tabCustom Field` set options=%s where fieldname='gst_state'", '\n'.join(states))
	frappe.db.sql("update `tabAddress` set gst_state='Chhattisgarh' where gst_state='Chattisgarh'")
	frappe.db.sql("update `tabAddress` set gst_state_number='05' where gst_state='Uttarakhand'")
