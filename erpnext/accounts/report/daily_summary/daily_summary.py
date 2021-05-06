# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _

def execute(filters=None):
	if not filters: filters = {}
	data = return_data(filters)
	columns = [_("Date") + "::240", _("Serie") + "::240", _("Transaction Type") + "::240", _("Range") + "::240", _("Exempts Sales") + ":Currency:120", _("Exonerated") + ":Currency:120", _("Taxed Sales 15%") + ":Currency:120", _("I.S.V 15%") + ":Currency:120", _("Taxed Sales 18%") + ":Currency:120", _("I.S.V 18%") + ":Currency:120", _("Total") + ":Currency:120"]
	return columns, data

def return_data(filters):
	data = []
	dates = []
	if filters.get("from_date"): from_date = filters.get("from_date")
	if filters.get("to_date"): to_date = filters.get("to_date")
	conditions = return_filters(filters, from_date, to_date)

	salary_slips = frappe.get_all("Sales Invoice", ["name", "creation_date", "naming_series", "posting_date", "authorized_range", "total_exempt", "total_exonerated", "taxed_sales15", "isv15", "taxed_sales18", "isv18", "grand_total"], filters = conditions, order_by = "name asc")

	for salary_slip in salary_slips:
		if len(dates) == 0:
			register = salary_slip.creation_date
			dates.append(register)
		else:
			new_date = False
			if salary_slip.creation_date in dates:
				new_date = False
			else:
				register = salary_slip.creation_date
				dates.append(register)

	dates_reverse = sorted(dates, reverse=False)
	
	for date in dates_reverse:		
		split_date = str(date).split("T")[0].split("-")
		posting_date = "-".join(reversed(split_date))
		serie_number = filters.get("serie")
		type_transaction = "FAC"
		initial_range = ""
		final_range = ""
		total_exempt = 0
		total_exonerated = 0
		taxed_sales15 = 0
		isv15 = 0
		taxed_sales18 = 0
		isv18 = 0
		is_row = False
		cont = 0

		for salary_slip in salary_slips:
			split_serie = salary_slip.naming_series.split('-')
			serie =  "{}-{}".format(split_serie[0], split_serie[1])		
				
			if date == salary_slip.creation_date and serie_number == serie:
				if cont == 0:
					split_initial_range = salary_slip.name.split("-")
					initial_range = split_initial_range[3]

				total_exempt += salary_slip.total_exempt
				total_exonerated += salary_slip.total_exonerated
				taxed_sales15 += salary_slip.taxed_sales15
				isv15 += salary_slip.isv15
				taxed_sales18 += salary_slip.taxed_sales18
				isv18 = salary_slip.isv18
				is_row = True
				split_final_range = salary_slip.name.split("-")
				final_range = split_final_range[3]
				cont += 1
		
		grand_total = taxed_sales15 + isv15 + taxed_sales18 + isv18 + total_exempt

		final_range = "{}-{}".format(initial_range, final_range)

		if is_row:
			row = [posting_date, serie_number, type_transaction, final_range, total_exempt, total_exonerated, taxed_sales15, isv15, taxed_sales18, isv18, grand_total]
			data.append(row)
	
	conditions = return_filters_debit_note(filters, from_date, to_date)

	debit_notes = frappe.get_all("Debit Note CXC", ["name", "naming_series", "posting_date", "isv_18", "isv_15", "outstanding_amount"], filters = conditions, order_by = "name asc")

	dates.clear()

	for debit_note in debit_notes:
		if len(dates) == 0:
			register = debit_note.posting_date
			dates.append(register)
		else:
			new_date = False
			if debit_note.posting_date in dates:
				new_date = False
			else:
				register = debit_note.posting_date
				dates.append(register)

	dates_reverse = sorted(dates, reverse=False)

	for date in dates_reverse:		
		split_date = str(date).split("T")[0].split("-")
		posting_date = "-".join(reversed(split_date))
		serie_number = filters.get("serie")
		type_transaction = "DN"
		initial_range = ""
		final_range = ""
		total_exempt = 0
		total_exonerated = 0
		taxed_sales15 = 0
		isv15 = 0
		taxed_sales18 = 0
		isv18 = 0
		is_row = False
		cont = 0

		for debit_note in debit_notes:
			split_serie = debit_note.naming_series.split('-')
			serie =  "{}-{}".format(split_serie[0], split_serie[1])		
				
			if date == debit_note.creation_date and serie_number == serie:
				if cont == 0:
					split_initial_range = debit_note.name.split("-")
					initial_range = split_initial_range[3]

				isv15 += debit_note.isv_15
				isv18 = debit_note.isv_18
				is_row = True
				split_final_range = debit_note.name.split("-")
				final_range = split_final_range[3]
				cont += 1

			multiples_taxes = frappe.get_all("Multiple Taxes", ["name", "isv", "base_isv"], filters = {"parent": debit_note.name})

			for multiple_taxe in multiples_taxes:
				item_tax_templates = frappe.get_all("Item Tax Template", ["name", "isv", "base_isv"], filters = {"parent": multiple_taxe.name})

				for tax_tamplate in item_tax_templates:

					tax_details = frappe.get_all("Item Tax Template Detail", ["name", "tax_rate"], filters = {"parent": tax_tamplate.name})
								
					for tax_detail in tax_details:

						if tax_detail.tax_rate == 15:
							taxed_sales15 += multiple_taxe.base_isv
								
						if tax_detail.tax_rate == 18:
							taxed_sales18 += multiple_taxe.base_isv							
		
		grand_total = taxed_sales15 + isv15 + taxed_sales18 + isv18 + total_exempt

		final_range = "{}-{}".format(initial_range, final_range)

		if is_row:
			row = [posting_date, serie_number, type_transaction, final_range, total_exempt, total_exonerated, taxed_sales15, isv15, taxed_sales18, isv18, grand_total]
			data.append(row)

	return data

def return_filters(filters, from_date, to_date):
	conditions = ''	

	conditions += "{"
	conditions += '"creation_date": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	conditions += '}'

	return conditions

def return_filters_debit_note(filters, from_date, to_date):
	conditions = ''	

	conditions += "{"
	conditions += '"posting_date": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	conditions += '}'

	return conditions
