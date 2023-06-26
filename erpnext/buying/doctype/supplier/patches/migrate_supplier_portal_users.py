import frappe


def execute():
	contact = frappe.qb.DocType("Contact")
	dynamic_link = frappe.qb.DocType("Dynamic Link")
	contacts = (
		frappe.qb.from_(contact)
		.inner_join(dynamic_link)
		.on(contact.name == dynamic_link.parent)
		.select(
			(dynamic_link.link_doctype).as_("doctype"),
			(dynamic_link.link_name).as_("parent"),
			(contact.email_id).as_("portal_user"),
		)
		.where(
			(dynamic_link.parenttype == "Contact")
			& (dynamic_link.link_doctype.isin(["Supplier", "Customer"]))
		)
	).run(as_dict=True)

	for contact in contacts:
		user = frappe.db.get_value("User", {"email": contact.portal_user}, "name")
		if user:
			portal_user_doc = frappe.new_doc("Portal User")
			portal_user_doc.parenttype = contact.doctype
			portal_user_doc.parentfield = "portal_users"
			portal_user_doc.parent = contact.parent
			portal_user_doc.user = user
			portal_user_doc.insert()
