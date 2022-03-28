import frappe


def update_lead_phone_numbers(contact, method):
	if contact.phone_nos:
		contact_lead = contact.get_link_for("Lead")
		if contact_lead:
			phone = mobile_no = contact.phone_nos[0].phone

			if len(contact.phone_nos) > 1:
				# get the default phone number
				primary_phones = [
					phone_doc.phone for phone_doc in contact.phone_nos if phone_doc.is_primary_phone
				]
				if primary_phones:
					phone = primary_phones[0]

				# get the default mobile number
				primary_mobile_nos = [
					phone_doc.phone for phone_doc in contact.phone_nos if phone_doc.is_primary_mobile_no
				]
				if primary_mobile_nos:
					mobile_no = primary_mobile_nos[0]

			lead = frappe.get_doc("Lead", contact_lead)
			lead.db_set("phone", phone)
			lead.db_set("mobile_no", mobile_no)


def copy_comments(doctype, docname, doc):
	comments = frappe.db.get_values(
		"Comment",
		filters={"reference_doctype": doctype, "reference_name": docname, "comment_type": "Comment"},
		fieldname="*",
	)
	for comment in comments:
		comment = frappe.get_doc(comment.update({"doctype": "Comment"}))
		comment.name = None
		comment.reference_doctype = doc.doctype
		comment.reference_name = doc.name
		comment.insert()


def add_link_in_communication(doctype, docname, doc):
	communication_list = get_linked_communication_list(doctype, docname)

	for communication in communication_list:
		communication_doc = frappe.get_doc("Communication", communication)
		communication_doc.add_link(doc.doctype, doc.name, autosave=True)


def get_linked_communication_list(doctype, docname):
	communications = frappe.get_all(
		"Communication", filters={"reference_doctype": doctype, "reference_name": docname}, pluck="name"
	)
	communication_links = frappe.get_all(
		"Communication Link",
		{"link_doctype": doctype, "link_name": docname, "parent": ("not in", communications)},
		pluck="parent",
	)

	return communications + communication_links
