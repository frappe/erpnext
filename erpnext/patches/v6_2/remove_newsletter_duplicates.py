import frappe

def execute():
	duplicates = frappe.db.sql("""select newsletter_list, email, count(name)
		from `tabNewsletter List Subscriber`
		group by newsletter_list, email
		having count(name) > 1""")

	# delete all duplicates except 1
	for newsletter_list, email, count in duplicates:
		frappe.db.sql("""delete from `tabNewsletter List Subscriber`
			where newsletter_list=%s and email=%s limit %s""", (newsletter_list, email, count-1))
