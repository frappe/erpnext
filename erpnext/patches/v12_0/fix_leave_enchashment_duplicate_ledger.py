import frappe
from erpnext.hr.doctype.leave_ledger_entry.leave_ledger_entry import process_expired_allocation


# Create function for duplicate entries
def execute():
	leave_encashments = get_leave_encashment_with_duplicate_ledger_entries()
	if leave_encashments:
		for name in leave_encashments:
			doc = frappe.get_doc('Leave Encashment', name)
			doc.create_leave_ledger_entry(submit=False)
			doc.create_leave_ledger_entry(submit=True)

		process_expired_allocation()


def get_leave_encashment_with_duplicate_ledger_entries():
	leave_encashment_duplicate_entries = frappe.db.sql_list("""
		SELECT transaction_name
		FROM `tabLeave Ledger Entry`
		WHERE transaction_type='Leave Encashment'
		GROUP BY transaction_name
		HAVING Count(name) > 1
	""")

	return leave_encashment_duplicate_entries
