import frappe
from frappe.utils import cstr


def execute():
	frappe.reload_doctype("Purchase Receipt Item")

	inter_company_precs = frappe.get_all("Purchase Receipt", filters={
		"inter_company_reference": ['is', 'set']
	})
	inter_company_precs = [d.name for d in inter_company_precs]

	for prec_name in inter_company_precs:
		purchase_receipt = frappe.get_doc("Purchase Receipt", prec_name)
		delivery_note = frappe.get_doc("Delivery Note", purchase_receipt.inter_company_reference)

		print("Purchase Receipt {0} <- Delivery Note {1}".format(purchase_receipt.name, delivery_note.name))

		delivery_item_map = {}
		for dn_item in delivery_note.get("items"):
			key = get_key(dn_item)

			if key in delivery_item_map:
				print("DUPLICATE KEY FOUND IN DELIVERY NOTE {0}: {1}".format(delivery_note.name, key))
			else:
				delivery_item_map[key] = dn_item

		for pr_item in purchase_receipt.get("items"):
			key = get_key(pr_item)
			dn_item = delivery_item_map.get(key)
			if not dn_item:
				frappe.throw("KEY {0} in Purchase Receipt {1} not found in Delivery Note {2}".format(
					key, purchase_receipt.name, delivery_note.name))

			pr_item.db_set("delivery_note_item", dn_item.name, update_modified=False)

			# set for returned against this row as well
			frappe.db.set_value("Purchase Receipt Item", {"purchase_receipt_item": pr_item.name},
				"delivery_note_item", dn_item.name, update_modified=False)


def get_key(row):
	return row.item_code, row.uom, cstr(row.batch_no), cstr(row.serial_no)
