from __future__ import unicode_literals
import frappe

def execute():
	subscriptions = frappe.get_all('Subscription', {'status': 'Active'})

	for d in subscriptions:
		subscription = frappe.get_doc('Subscription', d.name)

		invoices = [d.invoice for d in subscription.invoices]

		current_period_invoices = frappe.get_all('Sales Invoice', fields=['name'],
			filters={'from_date': subscription.current_invoice_start, 'to_date': subscription.current_invoice_end,
			'name': ('in', invoices), 'docstatus': 1, status: 'Unpaid'})

		current_invoices = [d.name for d in current_period_invoices]

		if len(current_invoices) > 1:
			for invoice in current_invoices[1:]:
				inv = frappe.get_doc('Sales Invoice', invoice)
				inv.cancel()

			frappe.db.sql("""
				DELETE from `tabSubscription Invoice`
				where invoice in (%s)""" % (','.join(['%s'] * len(current_invoices[1:]))),
				tuple(current_invoices[1:]))

			for inv in current_invoices[1:]:
				frappe.delete_doc('Sales Invoice', inv)
