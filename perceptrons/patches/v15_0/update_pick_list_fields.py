import frappe
from frappe.query_builder.functions import IfNull


def execute():
	update_delivery_note()
	update_pick_list_items()


def update_delivery_note():
	DN = frappe.qb.DocType("Delivery Note")
	DNI = frappe.qb.DocType("Delivery Note Item")

	frappe.qb.update(DNI).join(DN).on(DN.name == DNI.parent).set(DNI.against_pick_list, DN.pick_list).where(
		IfNull(DN.pick_list, "") != ""
	).run()


def update_pick_list_items():
	PL = frappe.qb.DocType("Pick List")
	PLI = frappe.qb.DocType("Pick List Item")

	pick_lists = frappe.qb.from_(PL).select(PL.name).where(PL.status == "Completed").run(pluck="name")

	if not pick_lists:
		return

	frappe.qb.update(PLI).set(PLI.delivered_qty, PLI.picked_qty).where(PLI.parent.isin(pick_lists)).run()
