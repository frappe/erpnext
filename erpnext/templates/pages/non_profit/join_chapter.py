import frappe


def get_context(context):
	context.no_cache = True
	chapter = frappe.get_doc("Chapter", frappe.form_dict.name)
	if frappe.session.user != "Guest":
		if frappe.session.user in [d.user for d in chapter.members if d.enabled == 1]:
			context.already_member = True
		else:
			if frappe.request.method == "GET":
				pass
			elif frappe.request.method == "POST":
				chapter.append(
					"members",
					dict(
						user=frappe.session.user,
						introduction=frappe.form_dict.introduction,
						website_url=frappe.form_dict.website_url,
						enabled=1,
					),
				)
				chapter.save(ignore_permissions=1)
				frappe.db.commit()

	context.chapter = chapter
