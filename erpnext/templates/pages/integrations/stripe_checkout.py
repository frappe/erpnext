# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cint, fmt_money
import json
from erpnext.erpnext_integrations.doctype.stripe_settings.stripe_settings import get_gateway_controller
from erpnext.erpnext_integrations.doctype.payment_plan.payment_plan import create_stripe_subscription

no_cache = 1
no_sitemap = 1

expected_keys = ('amount', 'title', 'description', 'reference_doctype', 'reference_docname',
	'payer_name', 'payer_email', 'order_id', 'currency')

def get_context(context):
	context.no_cache = 1

	# all these keys exist in form_dict
	if not (set(expected_keys) - set(list(frappe.form_dict))):
		for key in expected_keys:
			context[key] = frappe.form_dict[key]

		gateway_controller = get_gateway_controller(context.reference_docname)
		context.publishable_key = get_api_key(context.reference_docname, gateway_controller)
		context.image = get_header_image(context.reference_docname, gateway_controller)

		context['amount'] = fmt_money(amount=context['amount'], currency=context['currency'])

		if frappe.db.get_value(context.reference_doctype, context.reference_docname, "is_a_subscription"):
			payment_plan = frappe.db.get_value(context.reference_doctype, context.reference_docname, "payment_plan")
			recurrence = frappe.db.get_value("Payment Plan", payment_plan, "recurrence")

			context['amount'] = context['amount'] + " " + _(recurrence)

	else:
		frappe.redirect_to_message(_('Some information is missing'),
			_('Looks like someone sent you to an incomplete URL. Please ask them to look into it.'))
		frappe.local.flags.redirect_location = frappe.local.response.location
		raise frappe.Redirect

def get_api_key(doc, gateway_controller):
	publishable_key = frappe.db.get_value("Stripe Settings", gateway_controller, "publishable_key")
	if cint(frappe.form_dict.get("use_sandbox")):
		publishable_key = frappe.conf.sandbox_publishable_key

	return publishable_key

def get_header_image(doc, gateway_controller):
	header_image = frappe.db.get_value("Stripe Settings", gateway_controller, "header_img")
	return header_image

@frappe.whitelist(allow_guest=True)
def make_payment(stripe_token_id, data, reference_doctype=None, reference_docname=None):
	data = json.loads(data)

	data.update({
		"stripe_token_id": stripe_token_id
	})

	gateway_controller = get_gateway_controller(reference_docname)

	if frappe.db.get_value("Payment Request", reference_docname, 'is_a_subscription'):
		data =  create_stripe_subscription(gateway_controller, data)
	else:
		data =  frappe.get_doc("Stripe Settings", gateway_controller).create_request(data)

	frappe.db.commit()
	return data
