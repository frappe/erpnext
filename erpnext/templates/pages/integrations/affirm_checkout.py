from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
from erpnext_affirm.erpnext_affirm_integration.doctype.affirm_settings.affirm_settings import build_checkout_data, get_api_config

no_cache = 1
no_sitemap = 1

expected_keys = ('amount', 'title', 'description', 'reference_doctype', 'reference_docname',
	'payer_name', 'payer_email', 'order_id', 'currency')

def get_context(context):
	context.no_cache = 1
	context.affirm_api_config = get_api_config()

	# all these keys exist in form_dict
	if not (set(expected_keys) - set(frappe.form_dict.keys())):
		checkout = dict()
		for key in expected_keys:
			checkout[key] = frappe.form_dict[key]

		checkout['amount'] = flt(checkout['amount'])

		context['checkout_data'] = build_checkout_data(**checkout)

		return context

	else:
		frappe.redirect_to_message(_('Some information is missing'),
			_('Looks like someone sent you to an incomplete URL. Please ask them to look into it.'))
		frappe.local.flags.redirect_location = frappe.local.response.location
		raise frappe.Redirect
