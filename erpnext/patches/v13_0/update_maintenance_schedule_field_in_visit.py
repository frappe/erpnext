import frappe


def execute():
	frappe.reload_doctype("Maintenance Visit")
	frappe.reload_doctype("Maintenance Visit Purpose")

	# Updates the Maintenance Schedule link to fetch serial nos
	from frappe.query_builder.functions import Coalesce

	mvp = frappe.qb.DocType("Maintenance Visit Purpose")
	mv = frappe.qb.DocType("Maintenance Visit")

	frappe.qb.update(mv).join(mvp).on(mvp.parent == mv.name).set(
		mv.maintenance_schedule, Coalesce(mvp.prevdoc_docname, "")
	).where(
		(mv.maintenance_type == "Scheduled") & (mvp.prevdoc_docname.notnull()) & (mv.docstatus < 2)
	).run(
		as_dict=1
	)
