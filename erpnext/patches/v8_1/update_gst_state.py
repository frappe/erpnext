import frappe
from erpnext.regional.india import states

def execute():
	frappe.db.sql("update `tabCustom Field` set options=%s where fieldname='gst_state'", '\n'.join(states))
	frappe.db.sql("update `tabAddress` set gst_state='Chhattisgarh' where gst_state='Chattisgarh'")
