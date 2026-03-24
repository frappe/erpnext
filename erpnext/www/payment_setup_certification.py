import frappe
from pypika import Order

no_cache = 1


def get_context(context):
	if frappe.session.user != "Guest":
		context.all_certifications = get_all_certifications_of_a_member()
		context.show_sidebar = True


def get_all_certifications_of_a_member():
	"""Returns all certifications"""
	certified_consultant = frappe.qb.DocType("Certified Consultant")
	certification_application = frappe.qb.DocType("Certification Application")
	return (
		frappe.qb.from_(certified_consultant)
		.join(certification_application)
		.on(certified_consultant.certification_application == certification_application.name)
		.select(
			certified_consultant.name,
			certified_consultant.from_date,
			certified_consultant.to_date,
			certification_application.amount,
			certification_application.currency,
		)
		.where((certified_consultant.paid == 1) & (certified_consultant.email == frappe.session.user))
		.orderby(certified_consultant.to_date, order=Order.desc)
	).run(as_dict=True)
