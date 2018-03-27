import frappe

def execute():
	if frappe.db.exists("DocType", "Physician"):
		frappe.reload_doc("healthcare", "doctype", "physician")
		frappe.reload_doc("healthcare", "doctype", "physician_service_unit_schedule")

		if frappe.db.has_column('Physician', 'physician_schedule'):
			for doc in frappe.get_all('Physician'):
				_doc = frappe.get_doc('Physician', doc.name)
				if _doc.physician_schedule:
					_doc.append('physician_schedules', {'schedule': _doc.physician_schedule})
					_doc.save()
