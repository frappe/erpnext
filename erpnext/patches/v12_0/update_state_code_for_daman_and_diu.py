import frappe

from erpnext.regional.india import states


def execute():

	company = frappe.get_all('Company', filters = {'country': 'India'})
	if not company:
		return

	# Update options in gst_state custom field
	gst_state = frappe.get_doc('Custom Field', 'Address-gst_state')
	gst_state.options = '\n'.join(states)
	gst_state.save()

	# Update gst_state and state code in existing address
	frappe.db.sql("""
		UPDATE `tabAddress`
		SET
			gst_state = 'Dadra and Nagar Haveli and Daman and Diu',
			gst_state_number = 26
		WHERE gst_state = 'Daman and Diu'
	""")
