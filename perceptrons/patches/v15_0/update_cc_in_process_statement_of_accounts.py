import frappe


def execute():
	process_statement_of_accounts = frappe.qb.DocType("Process Statement Of Accounts")

	data = (
		frappe.qb.from_(process_statement_of_accounts)
		.select(process_statement_of_accounts.name, process_statement_of_accounts.cc_to)
		.where(process_statement_of_accounts.cc_to.isnotnull())
	).run(as_dict=True)

	for d in data:
		doc = frappe.get_doc("Process Statement Of Accounts", d.name)
		doc.append("cc_to", {"cc": d.cc_to})
		doc.save()
