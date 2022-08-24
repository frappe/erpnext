import frappe


# Create function for duplicate entries
def execute():
	duplicate_entries  = get_leave_encashment_with_duplicate_ledger_entries()
	if duplicate_entries:
		for duplicate_encashment in duplicate_entries:
			doc = frappe.get_doc('Leave Encashment',duplicate_encashment.get("transaction_name"))
			doc.create_leave_ledger_entry(submit=False)
			doc.create_leave_ledger_entry(submit=True)


def get_leave_encashment_with_duplicate_ledger_entries():
	leave_encashment_duplicate_entries = frappe.db.sql("""
		SELECT transaction_name
		FROM `tabLeave Ledger Entry`
		WHERE transaction_type='Leave Encashment'
		GROUP BY transaction_name
		HAVING Count(name) > 1
	""", as_dict =1)

	return leave_encashment_duplicate_entries