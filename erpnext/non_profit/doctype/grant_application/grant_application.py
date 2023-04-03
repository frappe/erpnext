# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.utils import get_url
from frappe.website.website_generator import WebsiteGenerator


class GrantApplication(WebsiteGenerator):
	_website = frappe._dict(
		condition_field="published",
	)

	def validate(self):
		if not self.route:  # pylint: disable=E0203
			self.route = "grant-application/" + self.scrub(self.name)

	def onload(self):
		"""Load address and contacts in `__onload`"""
		load_address_and_contact(self)

	def get_context(self, context):
		context.no_cache = True
		context.show_sidebar = True
		context.parents = [
			dict(label="View All Grant Applications", route="grant-application", title="View Grants")
		]


def get_list_context(context):
	context.allow_guest = True
	context.no_cache = True
	context.no_breadcrumbs = True
	context.show_sidebar = True
	context.order_by = "creation desc"
	context.introduction = """<a class="btn btn-primary" href="/my-grant?new=1">
		Apply for new Grant Application</a>"""


@frappe.whitelist()
def send_grant_review_emails(grant_application):
	grant = frappe.get_doc("Grant Application", grant_application)
	url = get_url("grant-application/{0}".format(grant_application))
	frappe.sendmail(
		recipients=grant.assessment_manager,
		sender=frappe.session.user,
		subject="Grant Application for {0}".format(grant.applicant_name),
		message="<p> Please Review this grant application</p><br>" + url,
		reference_doctype=grant.doctype,
		reference_name=grant.name,
	)

	grant.status = "In Progress"
	grant.email_notification_sent = 1
	grant.save()
	frappe.db.commit()

	frappe.msgprint(_("Review Invitation Sent"))
