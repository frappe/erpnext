import frappe
from frappe.query_builder.functions import IfNull


def execute():
	update_delivery_note()
	update_pick_list_items()


def update_delivery_note():
	# Postgres doesn't support UPDATE ... JOIN. Use UPDATE ... FROM instead.
	frappe.db.multisql(
		{
			"mariadb": """
				UPDATE `tabDelivery Note Item` dni
				JOIN `tabDelivery Note` dn ON dn.`name` = dni.`parent`
				SET dni.`against_pick_list` = dn.`pick_list`
				WHERE COALESCE(dn.`pick_list`, '') <> ''
			""",
			"postgres": """
				UPDATE "tabDelivery Note Item" dni
				SET against_pick_list = dn.pick_list
				FROM "tabDelivery Note" dn
				WHERE dn.name = dni.parent
				  AND COALESCE(dn.pick_list, '') <> ''
			""",
		}
	)


def update_pick_list_items():
	PL = frappe.qb.DocType("Pick List")
	PLI = frappe.qb.DocType("Pick List Item")

	pick_lists = frappe.qb.from_(PL).select(PL.name).where(PL.status == "Completed").run(pluck="name")

	if not pick_lists:
		return

	frappe.qb.update(PLI).set(PLI.delivered_qty, PLI.picked_qty).where(PLI.parent.isin(pick_lists)).run()
