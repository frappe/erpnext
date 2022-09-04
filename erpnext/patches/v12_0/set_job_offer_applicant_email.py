import frappe


def execute():
	frappe.reload_doc("hr", "doctype", "job_offer")

	frappe.db.sql(
		"""
		UPDATE
			`tabJob Offer` AS offer
		SET
			applicant_email = (SELECT email_id FROM `tabJob Applicant` WHERE name = offer.job_applicant)
	"""
	)
