# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _

def execute(filters=None):
	if not filters: filters = {}
	columns = [_("Date") + "::240", _("RTN") + "::240", _("Name or Social reason") + "::240", _("Transaction Type") + "::240", _("Serie") + "::240", _("Document Number") + "::240", _("CAI") + "::240", _("Gross Amount") + ":Currency:120", _("Exempts Sales") + ":Currency:120", _("Exonerated") + ":Currency:120", _("Taxed Sales 15%") + ":Currency:120", _("I.S.V 15%") + ":Currency:120", _("Taxed Sales 18%") + ":Currency:120", _("I.S.V 18%") + ":Currency:120", _("Partial Discount") + ":Currency:120" ,_("Discount Amount") + ":Currency:120", _("Total") + ":Currency:120"]
	data = return_data(filters)
	return columns, data

def return_data(filters):
	data = []
	if filters.get("from_date"): from_date = filters.get("from_date")
	if filters.get("to_date"): to_date = filters.get("to_date")
	conditions = return_filters(filters, from_date, to_date)

	salary_slips = frappe.get_all("Sales Invoice", ["name", "status","creation_date", "rtn", "client_name", "cai", "naming_series", "posting_date", "authorized_range", "total_exempt", "total_exonerated", "taxed_sales15", "isv15", "taxed_sales18", "isv18", "grand_total", "discount_amount", "partial_discount", "total"], filters = conditions, order_by = "name asc")	

	for salary_slip in salary_slips:
		split_date = str(salary_slip.posting_date).split("T")[0].split("-")
		posting_date = "-".join(reversed(split_date))
		serie_number = filters.get("prefix")	
		type_transaction = "FAC"
		initial_range = ""
		final_range = ""
		total_exempt = 0
		gross = 0
		total_exonerated = 0
		taxed_sales15 = 0
		isv15 = 0
		taxed_sales18 = 0
		isv18 = 0
		rtn = salary_slip.rtn
		partial_discount = 0
		discount_amount = 0
		grand_total = 0

		split_serie = salary_slip.naming_series.split('-')
		serie =  "{}-{}".format(split_serie[0], split_serie[1])		

		if serie_number == serie and salary_slip.status != "Return":	
			total_exempt = salary_slip.total_exempt
			gross += salary_slip.total
			total_exonerated = salary_slip.total_exonerated
			taxed_sales15 = salary_slip.taxed_sales15
			isv15 += salary_slip.isv15
			taxed_sales18 = salary_slip.taxed_sales18
			isv18 = salary_slip.isv18
			partial_discount += salary_slip.partial_discount
			discount_amount += salary_slip.discount_amount
			grand_total += salary_slip.grand_total
			is_row = True
			split_final_range = salary_slip.name.split("-")
			final_range = split_final_range[3]

			final_range = "{}-{}".format(initial_range, final_range)

			row = [posting_date, rtn, salary_slip.client_name, type_transaction, serie_number,salary_slip.name, salary_slip.cai, gross,total_exempt, total_exonerated, taxed_sales15, isv15, taxed_sales18, isv18, partial_discount, discount_amount, grand_total]
			data.append(row)
	
	for salary_slip in salary_slips:
		split_date = str(salary_slip.posting_date).split("T")[0].split("-")
		posting_date = "-".join(reversed(split_date))
		serie_number = filters.get("prefix")	
		type_transaction = "DEV"
		initial_range = ""
		final_range = ""
		total_exempt = 0
		gross = 0
		total_exonerated = 0
		taxed_sales15 = 0
		isv15 = 0
		taxed_sales18 = 0
		isv18 = 0
		rtn = salary_slip.rtn
		partial_discount = 0
		discount_amount = 0

		split_serie = salary_slip.naming_series.split('-')
		serie =  "{}-{}".format(split_serie[0], split_serie[1])		

		if serie_number == serie and salary_slip.status == "Return":	
			total_exempt = salary_slip.total_exempt
			gross += salary_slip.total
			total_exonerated = salary_slip.total_exonerated
			taxed_sales15 = salary_slip.taxed_sales15
			isv15 += salary_slip.isv15
			taxed_sales18 = salary_slip.taxed_sales18
			isv18 = salary_slip.isv18
			partial_discount += salary_slip.partial_discount
			discount_amount += salary_slip.discount_amount
			grand_total += salary_slip.grand_total
			is_row = True
			split_final_range = salary_slip.name.split("-")
			final_range = split_final_range[3]

			final_range = "{}-{}".format(initial_range, final_range)

			row = [posting_date, rtn, salary_slip.client_name, type_transaction, serie_number,salary_slip.name, salary_slip.cai, gross, total_exempt, total_exonerated, taxed_sales15, isv15, taxed_sales18, isv18, partial_discount, discount_amount, grand_total]
			data.append(row)

	conditions = return_filters_debit_note(filters, from_date, to_date)

	debit_notes = frappe.get_all("Debit Note CXC", ["name", "customer", "cai", "naming_series", "posting_date", "isv_18", "isv_15", "outstanding_amount"], filters = conditions, order_by = "name asc")

	for debit_note in debit_notes:
		split_date = str(debit_note.posting_date).split("T")[0].split("-")
		posting_date = "-".join(reversed(split_date))
		serie_number = filters.get("prefix")
		type_transaction = "DN"
		initial_range = ""
		final_range = ""
		total_exempt = 0
		total_exonerated = 0
		taxed_sales15 = 0
		isv15 = 0
		taxed_sales18 = 0
		isv18 = 0
		split_serie = debit_note.naming_series.split('-')
		serie =  "{}-{}".format(split_serie[0], split_serie[1])		
		rtn = ""

		if serie_number == serie:
			split_initial_range = debit_note.name.split("-")
			initial_range = split_initial_range[3]

			isv15 += debit_note.isv_15
			isv18 = debit_note.isv_18
			split_final_range = debit_note.name.split("-")
			final_range = split_final_range[3]

			multiples_taxes = frappe.get_all("Multiple Taxes", ["name", "base_isv", "isv"], filters = {"parent": debit_note.name})

			for multiple_taxe in multiples_taxes:
				item_tax_templates = frappe.get_all("Item Tax Template", ["name"], filters = {"name": multiple_taxe.isv})

				for tax_tamplate in item_tax_templates:

					tax_details = frappe.get_all("Item Tax Template Detail", ["name", "tax_rate"], filters = {"parent": tax_tamplate.name})
								
					for tax_detail in tax_details:

						if tax_detail.tax_rate == 15:
							taxed_sales15 += multiple_taxe.base_isv
								
						if tax_detail.tax_rate == 18:
							taxed_sales18 += multiple_taxe.base_isv							
		
			grand_total = taxed_sales15 + isv15 + taxed_sales18 + isv18 + total_exempt

			final_range = "{}-{}".format(initial_range, final_range)

			row = [posting_date,rtn,debit_note.customer, type_transaction, serie_number, debit_note.name, debit_note.cai, grand_total, total_exempt, total_exonerated, taxed_sales15, isv15, taxed_sales18, isv18, 0, 0, grand_total]
			data.append(row)
	
	conditions = return_filters_credit_note(filters, from_date, to_date)
	
	credit_notes = frappe.get_all("Credit Note CXC", ["name", "customer", "cai", "naming_series", "posting_date", "isv_18", "isv_15", "amount_total", "total_exempt"], filters = conditions, order_by = "name asc")

	for credit_note in credit_notes:
		split_date = str(credit_note.posting_date).split("T")[0].split("-")
		posting_date = "-".join(reversed(split_date))
		serie_number = filters.get("prefix")
		type_transaction = "CN"
		initial_range = ""
		final_range = ""
		total_exempt = 0
		total_exonerated = 0
		taxed_sales15 = 0
		isv15 = 0
		taxed_sales18 = 0
		isv18 = 0
		split_serie = credit_note.naming_series.split('-')
		serie =  "{}-{}".format(split_serie[0], split_serie[1])		
		rtn = ""

		if serie_number == serie:
			split_initial_range = credit_note.name.split("-")
			initial_range = split_initial_range[3]

			isv15 += credit_note.isv_15
			isv18 += credit_note.isv_18
			split_final_range = credit_note.name.split("-")
			final_range = split_final_range[3]
			total_exempt += credit_note.total_exempt

			multiples_taxes = frappe.get_all("Multiple Taxes", ["name", "base_isv", "isv_template"], filters = {"parent": credit_note.name})

			for multiple_taxe in multiples_taxes:
				item_tax_templates = frappe.get_all("Item Tax Template", ["name"], filters = {"name": multiple_taxe.isv_template})

				for tax_tamplate in item_tax_templates:

					tax_details = frappe.get_all("Item Tax Template Detail", ["name", "tax_rate"], filters = {"parent": tax_tamplate.name})
								
					for tax_detail in tax_details:

						if tax_detail.tax_rate == 15:
							taxed_sales15 += multiple_taxe.base_isv
								
						if tax_detail.tax_rate == 18:
							taxed_sales18 += multiple_taxe.base_isv							
		
			grand_total = taxed_sales15 + isv15 + taxed_sales18 + isv18 + total_exempt

			final_range = "{}-{}".format(initial_range, final_range)

			row = [posting_date,rtn,credit_note.customer, type_transaction, serie_number, credit_note.name, credit_note.cai, grand_total, total_exempt, total_exonerated, taxed_sales15, isv15, taxed_sales18, isv18, 0, 0, grand_total]
			data.append(row)
	
	conditions = return_filters_customer_retention(filters, from_date, to_date)

	customer_retentions = frappe.get_all("Customer Retention", ["name", "rtn", "posting_date", "customer", "cai", "naming_series"], filters = conditions, order_by = "name asc")

	for customer_retetention in customer_retentions:
		total_exempt = 0
		total_exonerated = 0
		taxed_sales15 = 0
		isv15 = 0
		taxed_sales18 = 0
		isv18 = 0
		grand_total = 0
		type_transaction = "CR"
		split_serie = customer_retetention.naming_series.split('-')
		serie =  "{}-{}".format(split_serie[0], split_serie[1])

		if serie_number == serie:
			withholding_references = frappe.get_all("Withholding Reference", ["reference_name"], filters = {"parent": customer_retetention.name})

			for withholding_reference in withholding_references:
				sales_invoices_customer_retention = frappe.get_all("Sales Invoice", ["total_exempt", "total_exonerated", "taxed_sales15", "isv15", "taxed_sales18", "isv18", "grand_total"], filters = {"name" : withholding_reference.reference_name})

				for sales_invoice_customer_retention in sales_invoices_customer_retention:
					total_exempt += sales_invoice_customer_retention.total_exempt
					total_exonerated += sales_invoice_customer_retention.total_exonerated
					taxed_sales15 += sales_invoice_customer_retention.taxed_sales15
					isv15 += sales_invoice_customer_retention.isv15
					taxed_sales18 += sales_invoice_customer_retention.taxed_sales18
					isv18 += sales_invoice_customer_retention.isv18
					grand_total += sales_invoice_customer_retention.grand_total
		
			row = [customer_retetention.posting_date, customer_retetention.rtn,customer_retetention.customer, type_transaction, serie_number, customer_retetention.name, customer_retetention.cai, grand_total, total_exempt, total_exonerated, taxed_sales15, isv15, taxed_sales18, isv18, 0, 0, grand_total]
			data.append(row)

	conditions = return_filters(filters, from_date, to_date)

	salary_slips = frappe.get_all("Return credit notes", ["name", "status","creation_date", "rtn", "client_name", "cai", "naming_series", "posting_date", "authorized_range", "total_exempt", "total_exonerated", "taxed_sales15", "isv15", "taxed_sales18", "isv18", "grand_total", "discount_amount", "partial_discount", "total"], filters = conditions, order_by = "name asc")	

	for salary_slip in salary_slips:
		split_date = str(salary_slip.posting_date).split("T")[0].split("-")
		posting_date = "-".join(reversed(split_date))
		serie_number = filters.get("prefix")	
		type_transaction = "DEV"
		initial_range = ""
		final_range = ""
		total_exempt = 0
		gross = 0
		total_exonerated = 0
		taxed_sales15 = 0
		isv15 = 0
		taxed_sales18 = 0
		isv18 = 0
		rtn = salary_slip.rtn
		partial_discount = 0
		discount_amount = 0
		grand_total = 0

		split_serie = salary_slip.naming_series.split('-')
		serie =  "{}-{}".format(split_serie[0], split_serie[1])			

		if serie_number == serie and salary_slip.status != "Return":	
			total_exempt = salary_slip.total_exempt
			gross += salary_slip.total
			total_exonerated = salary_slip.total_exonerated
			taxed_sales15 = salary_slip.taxed_sales15
			isv15 += salary_slip.isv15
			taxed_sales18 = salary_slip.taxed_sales18
			isv18 = salary_slip.isv18
			partial_discount += salary_slip.partial_discount
			discount_amount += salary_slip.discount_amount
			grand_total += salary_slip.grand_total
			is_row = True
			split_final_range = salary_slip.name.split("-")
			final_range = split_final_range[3]

			final_range = "{}-{}".format(initial_range, final_range)

			row = [posting_date, rtn, salary_slip.client_name, type_transaction, serie_number,salary_slip.name, salary_slip.cai, gross,total_exempt, total_exonerated, taxed_sales15, isv15, taxed_sales18, isv18, partial_discount, discount_amount, grand_total]
			data.append(row)

	return data

def return_filters(filters, from_date, to_date):
	conditions = ''	

	conditions += "{"
	conditions += '"posting_date": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	conditions += ', "company": "{}"'.format(filters.get("company"))
	conditions += ', "status": ["!=", "Canceled"]'
	conditions += '}'

	return conditions

def return_filters_debit_note(filters, from_date, to_date):
	conditions = ''	

	conditions += "{"
	conditions += '"posting_date": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	conditions += ', "company": "{}"'.format(filters.get("company"))
	conditions += '}'

	return conditions

def return_filters_credit_note(filters, from_date, to_date):
	conditions = ''	

	conditions += "{"
	conditions += '"posting_date": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	conditions += ', "company": "{}"'.format(filters.get("company"))
	conditions += '}'

	return conditions

def return_filters_customer_retention(filters, from_date, to_date):
	conditions = ''	

	conditions += "{"
	conditions += '"posting_date": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	conditions += ', "company": "{}"'.format(filters.get("company"))
	conditions += '}'

	return conditions
