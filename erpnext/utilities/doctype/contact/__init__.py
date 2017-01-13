from __future__ import unicode_literals
import frappe

def match_email_to_contact(doc,method=None):
	if doc.communication_type == "Communication":
		origin_contact = frappe.db.sql(
			"select name, email_id, supplier, supplier_name, customer, customer_name, user, organisation from `tabContact` where email_id <>''",
			as_dict=1)
		for comm in origin_contact:
			if comm.email_id:
				if (doc.sender and doc.sent_or_received == "Received" and doc.sender.find(comm.email_id) > -1) or (
								doc.recipients and doc.sent_or_received == "Sent" and doc.recipients.find(
							comm.email_id) > -1):
					if sum(1 for x in [comm.supplier, comm.customer, comm.user, comm.organisation] if x) > 1:
						doc.db_set("timeline_doctype", "Contact")
						doc.db_set("timeline_name", comm.name)
						doc.db_set("timeline_label", doc.name)

					elif comm.supplier:
						doc.db_set("timeline_doctype", "Supplier")
						doc.db_set("timeline_name", comm.supplier)
						doc.db_set("timeline_label", comm.supplier_name)

					elif comm.customer:
						doc.db_set("timeline_doctype", "Customer")
						doc.db_set("timeline_name", comm.customer)
						doc.db_set("timeline_label", comm.customer_name)
					elif comm.user:
						doc.db_set("timeline_doctype", "User")
						doc.db_set("timeline_name", comm.user)
						doc.db_set("timeline_label", comm.user)
					elif comm.organisation:
						doc.db_set("timeline_doctype", "Organisation")
						doc.db_set("timeline_name", comm.organisation)
						doc.db_set("timeline_label", comm.organisation)
					else:
						doc.db_set("timeline_doctype", None)
						doc.db_set("timeline_name", None)
						doc.db_set("timeline_label", None)
