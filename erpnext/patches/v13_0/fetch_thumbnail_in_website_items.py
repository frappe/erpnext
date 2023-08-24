import frappe


def execute():
	if frappe.db.has_column("Item", "thumbnail"):
		website_item = frappe.qb.DocType("Website Item").as_("wi")
		item = frappe.qb.DocType("Item")

		frappe.qb.update(website_item).inner_join(item).on(website_item.item_code == item.item_code).set(
			website_item.thumbnail, item.thumbnail
		).where(website_item.website_image.notnull() & website_item.thumbnail.isnull()).run()
