import frappe


def execute():
	contact = frappe.qb.DocType("Contact")
	dynamic_link = frappe.qb.DocType("Dynamic Link")
	q = (
		frappe.qb.from_(contact)
		.inner_join(dynamic_link)
		.on(contact.name == dynamic_link.parent)
		.select(
			(dynamic_link.link_doctype).as_("doctype"),
			(dynamic_link.link_name).as_("parent"),
			(contact.user).as_("portal_user"),
		)
		.where(
			(dynamic_link.parenttype == "Contact")
			& (dynamic_link.link_doctype.isin(["Supplier", "Customer"]))
		)
	)
	contacts = q.run(as_dict=True, debug=True)
	for contact in contacts:
		portal_user_doc = frappe.new_doc("Portal User")
		portal_user_doc.parenttype = contact.doctype
		portal_user_doc.parentfield = "portal_users"
		portal_user_doc.parent = contact.parent
		portal_user_doc.user = contact.portal_user
		portal_user_doc.save()
		user_doc = frappe.get_doc("User", contact.portal_user)
		user_doc.add_roles(contact.doctype)
		user_doc.save()
