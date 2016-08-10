# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import get_url, flt
import json, urllib

from erpnext.integrations.razorpay import Controller

no_cache = 1
no_sitemap = 1

expected_keys = ('amount', 'title', 'description', 'reference_doctype', 'reference_docname',
	'payer_name', 'payer_email', 'order_id')

def get_context(context):
	context.no_cache = 1
	context.api_key = Controller().get_settings().api_key

	context.brand_image = (frappe.db.get_value("Razorpay Settings", None, "brand_image")
		or './assets/erpnext/images/erp-icon.svg')

	# all these keys exist in form_dict
	if not (set(expected_keys) - set(frappe.form_dict.keys())):
		for key in expected_keys:
			context[key] = frappe.form_dict[key]

		context['amount'] = flt(context['amount'])

	else:
		frappe.redirect_to_message(_('Some information is missing'), _('Looks like someone sent you to an incomplete URL. Please ask them to look into it.'))
		frappe.local.flags.redirect_location = frappe.local.response.location
		raise frappe.Redirect

def get_checkout_url(**kwargs):
	missing_keys = set(expected_keys) - set(kwargs.keys())
	if missing_keys:
		frappe.throw(_('Missing keys to build checkout URL: {0}').format(", ".join(list(missing_keys))))

	return get_url('/razorpay_checkout?{0}'.format(urllib.urlencode(kwargs)))

@frappe.whitelist(allow_guest=True)
def make_payment(razorpay_payment_id, options, reference_doctype, reference_docname):
	data = {}
	
	if isinstance(options, basestring):
		data = json.loads(options)
	
	data.update({
		"razorpay_payment_id": razorpay_payment_id,
		"reference_docname": reference_docname,
		"reference_doctype": reference_doctype
	})
	
	return Controller().make_integration_request(data)
