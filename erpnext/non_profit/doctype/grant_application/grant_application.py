# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.website.website_generator import WebsiteGenerator
from frappe.contacts.address_and_contact import load_address_and_contact

class GrantApplication(WebsiteGenerator):
	_website = frappe._dict(
		condition_field = "published",
	)

	def validate(self):
		if not self.route:		#pylint: disable=E0203
			self.route = 'grant-application/' + self.scrub(self.name)

	def onload(self):
		"""Load address and contacts in `__onload`"""
		load_address_and_contact(self)


def get_list_context(context):
	context.allow_guest = True
	context.no_cache = True
	context.no_breadcrumbs = True
	context.order_by = 'creation desc'
	context.introduction ='<div>Grant Application List</div><br><a class="btn btn-primary" href="/my-grant?new=1">Apply for new Grant Application</a>'

@frappe.whitelist(allow_guest=True)
def assessment_result(title, assessment_scale, note):
	vote = frappe.get_doc("Grant Application", title)
	vote.assessment_scale = assessment_scale
	vote.note = note
	vote.save()
	frappe.db.commit()
	return "Thank you for Assessment Review"