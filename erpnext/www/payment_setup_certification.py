import frappe
from frappe.query_builder.functions import IfNull

no_cache = 1


def get_context(context):
	if frappe.session.user != "Guest":
		context.all_certifications = get_all_certifications_of_a_member()
		context.show_sidebar = True


def get_all_certifications_of_a_member():
	"""Returns all certifications"""
	all_certifications = []
	cc = frappe.qb.DocType("Certified Consultant")
	ca = frappe.qb.DocType("Certification Application")
	all_certifications = (
		frappe.qb.from_(cc)
		.inner_join(ca)
		.on(cc.certification_application == ca.name)
		.select(cc.name, cc.from_date, cc.to_date, ca.amount, ca.currency)
		.where((cc.paid == 1) & (cc.email == frappe.session.user))
		.orderby(IfNull(cc.to_date, "0001-01-01"), order=frappe.qb.desc)
		.run(as_dict=True)
	)
	return all_certifications
