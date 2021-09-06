from __future__ import unicode_literals

import frappe
from frappe.utils import flt

import erpnext
from erpnext.setup.utils import get_exchange_rate


def execute():
	frappe.reload_doc('crm', 'doctype', 'opportunity')
	frappe.reload_doc('crm', 'doctype', 'opportunity_item')

	opportunities = frappe.db.get_list('Opportunity', filters={
		'opportunity_amount': ['>', 0]
	}, fields=['name', 'company', 'currency', 'opportunity_amount'])

	for opportunity in opportunities:
		company_currency = erpnext.get_company_currency(opportunity.company)

		# base total and total will be 0 only since item table did not have amount field earlier
		if opportunity.currency != company_currency:
			conversion_rate = get_exchange_rate(opportunity.currency, company_currency)
			base_opportunity_amount = flt(conversion_rate) * flt(opportunity.opportunity_amount)
			grand_total = flt(opportunity.opportunity_amount)
			base_grand_total = flt(conversion_rate) * flt(opportunity.opportunity_amount)
		else:
			conversion_rate = 1
			base_opportunity_amount = grand_total = base_grand_total = flt(opportunity.opportunity_amount)

		frappe.db.set_value('Opportunity', opportunity.name, {
			'conversion_rate': conversion_rate,
			'base_opportunity_amount': base_opportunity_amount,
			'grand_total': grand_total,
			'base_grand_total': base_grand_total
		}, update_modified=False)
