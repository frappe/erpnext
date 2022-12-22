import frappe
from frappe.utils import nowdate

from erpnext.accounts.utils import FiscalYearError, get_fiscal_year


def execute():
	# Only do for current fiscal year, no need to repost for all years
	for company in frappe.get_all("Company"):
		try:
			fiscal_year_details = get_fiscal_year(date=nowdate(), company=company.name, as_dict=True)

			purchase_invoice = frappe.qb.DocType("Purchase Invoice")

			frappe.qb.update(purchase_invoice).set(
				purchase_invoice.tax_withholding_net_total, purchase_invoice.net_total
			).set(
				purchase_invoice.base_tax_withholding_net_total, purchase_invoice.base_net_total
			).where(
				purchase_invoice.company == company.name
			).where(
				purchase_invoice.apply_tds == 1
			).where(
				purchase_invoice.posting_date >= fiscal_year_details.year_start_date
			).where(
				purchase_invoice.docstatus == 1
			).run()

			purchase_order = frappe.qb.DocType("Purchase Order")

			frappe.qb.update(purchase_order).set(
				purchase_order.tax_withholding_net_total, purchase_order.net_total
			).set(
				purchase_order.base_tax_withholding_net_total, purchase_order.base_net_total
			).where(
				purchase_order.company == company.name
			).where(
				purchase_order.apply_tds == 1
			).where(
				purchase_order.transaction_date >= fiscal_year_details.year_start_date
			).where(
				purchase_order.docstatus == 1
			).run()
		except FiscalYearError:
			pass
