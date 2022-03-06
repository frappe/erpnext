import frappe


def execute():
    "Copy website_image field from Item if image is not already populated"
    for website_item_name in frappe.db.get_list(
        "Website Item", {"image": ("=", "")}, pluck="name"
    ):
        witem = frappe.get_doc("Website Item", website_item_name)
        image = frappe.db.get_value("Item", witem.item_code, "website_image")
        witem.image = image
        witem.save()
