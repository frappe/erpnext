# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from frappe import _
from frappe.utils import flt, formatdate, now_datetime, getdate
from datetime import date
from six import iteritems
from erpnext.regional.doctype.gstr_3b_report.gstr_3b_report import get_period
from erpnext.regional.india.utils import get_gst_accounts

def execute(filters=None):
	return Gstr1Report(filters).run()

class Gstr1Report(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.columns = []
		self.data = []
		self.doctype = "Sales Invoice"
		self.tax_doctype = "Sales Taxes and Charges"
		self.select_columns = """
			name as invoice_number,
			customer_name,
			posting_date,
			base_grand_total,
			base_rounded_total,
			COALESCE(NULLIF(customer_gstin,''), NULLIF(billing_address_gstin, '')) as customer_gstin,
			place_of_supply,
			ecommerce_gstin,
			reverse_charge,
			return_against,
			is_return,
			gst_category,
			export_type,
			port_code,
			shipping_bill_number,
			shipping_bill_date,
			reason_for_issuing_document
		"""

	def run(self):
		self.get_columns()
		self.gst_accounts = get_gst_accounts(self.filters.company)
		self.get_invoice_data()

		if self.invoices:
			self.get_invoice_items()
			self.get_items_based_on_tax_rate()
			self.invoice_fields = [d["fieldname"] for d in self.invoice_columns]
			self.get_data()

		return self.columns, self.data

	def get_data(self):
		if self.filters.get("type_of_business") in  ("B2C Small", "B2C Large"):
			self.get_b2c_data()
		else:
			for inv, items_based_on_rate in self.items_based_on_tax_rate.items():
				invoice_details = self.invoices.get(inv)
				for rate, items in items_based_on_rate.items():
					row, taxable_value = self.get_row_data_for_invoice(inv, invoice_details, rate, items)

					if self.filters.get("type_of_business") ==  "CDNR":
						row.append("Y" if invoice_details.posting_date <= date(2017, 7, 1) else "N")
						row.append("C" if invoice_details.return_against else "R")

					if taxable_value:
						self.data.append(row)

	def get_b2c_data(self):
		b2cs_output = {}

		for inv, items_based_on_rate in self.items_based_on_tax_rate.items():
			invoice_details = self.invoices.get(inv)
			for rate, items in items_based_on_rate.items():
				place_of_supply = invoice_details.get("place_of_supply")
				ecommerce_gstin =  invoice_details.get("ecommerce_gstin")

				b2cs_output.setdefault((rate, place_of_supply, ecommerce_gstin, inv),{
					"place_of_supply": "",
					"ecommerce_gstin": "",
					"rate": "",
					"taxable_value": 0,
					"cess_amount": 0,
					"type": "",
					"invoice_number": invoice_details.get("invoice_number"),
					"posting_date": invoice_details.get("posting_date"),
					"invoice_value": invoice_details.get("base_grand_total"),
				})

				row = b2cs_output.get((rate, place_of_supply, ecommerce_gstin, inv))
				row["place_of_supply"] = place_of_supply
				row["ecommerce_gstin"] = ecommerce_gstin
				row["rate"] = rate
				row["taxable_value"] += sum([abs(net_amount)
					for item_code, net_amount in self.invoice_items.get(inv).items() if item_code in items])
				row["cess_amount"] += flt(self.invoice_cess.get(inv), 2)
				row["type"] = "E" if ecommerce_gstin else "OE"

		for key, value in iteritems(b2cs_output):
			self.data.append(value)

	def get_row_data_for_invoice(self, invoice, invoice_details, tax_rate, items):
		row = []
		for fieldname in self.invoice_fields:
			if self.filters.get("type_of_business") ==  "CDNR" and fieldname == "invoice_value":
				row.append(abs(invoice_details.base_rounded_total) or abs(invoice_details.base_grand_total))
			elif fieldname == "invoice_value":
				row.append(invoice_details.base_rounded_total or invoice_details.base_grand_total)
			elif fieldname in ('posting_date', 'shipping_bill_date'):
				row.append(formatdate(invoice_details.get(fieldname), 'dd-MMM-YY'))
			elif fieldname == "export_type":
				export_type = "WPAY" if invoice_details.get(fieldname)=="With Payment of Tax" else "WOPAY"
				row.append(export_type)
			else:
				row.append(invoice_details.get(fieldname))
		taxable_value = 0

		if invoice in self.cgst_sgst_invoices:
			division_factor = 2
		else:
			division_factor = 1

		for item_code, net_amount in self.invoice_items.get(invoice).items():
			if item_code in items:
				if self.item_tax_rate.get(invoice) and tax_rate/division_factor in self.item_tax_rate.get(invoice, {}).get(item_code, []):
					taxable_value += abs(net_amount)
				elif not self.item_tax_rate.get(invoice):
					taxable_value += abs(net_amount)
				elif tax_rate:
					taxable_value += abs(net_amount)
				elif not tax_rate and self.filters.get('type_of_business') == 'EXPORT' \
					and invoice_details.get('export_type') == "Without Payment of Tax":
					taxable_value += abs(net_amount)

		row += [tax_rate or 0, taxable_value]

		for column in self.other_columns:
			if column.get('fieldname') == 'cess_amount':
				row.append(flt(self.invoice_cess.get(invoice), 2))

		return row, taxable_value

	def get_invoice_data(self):
		self.invoices = frappe._dict()
		conditions = self.get_conditions()
		invoice_data = frappe.db.sql("""
			select
				{select_columns}
			from `tab{doctype}`
			where docstatus = 1 {where_conditions}
			and is_opening = 'No'
			order by posting_date desc
			""".format(select_columns=self.select_columns, doctype=self.doctype,
				where_conditions=conditions), self.filters, as_dict=1)

		for d in invoice_data:
			self.invoices.setdefault(d.invoice_number, d)

	def get_conditions(self):
		conditions = ""

		for opts in (("company", " and company=%(company)s"),
			("from_date", " and posting_date>=%(from_date)s"),
			("to_date", " and posting_date<=%(to_date)s"),
			("company_address", " and company_address=%(company_address)s")):
				if self.filters.get(opts[0]):
					conditions += opts[1]


		if self.filters.get("type_of_business") ==  "B2B":
			conditions += "and ifnull(gst_category, '') in ('Registered Regular', 'Deemed Export', 'SEZ') and is_return != 1"

		if self.filters.get("type_of_business") in ("B2C Large", "B2C Small"):
			b2c_limit = frappe.db.get_single_value('GST Settings', 'b2c_limit')
			if not b2c_limit:
				frappe.throw(_("Please set B2C Limit in GST Settings."))

		if self.filters.get("type_of_business") ==  "B2C Large":
			conditions += """ and ifnull(SUBSTR(place_of_supply, 1, 2),'') != ifnull(SUBSTR(company_gstin, 1, 2),'')
				and grand_total > {0} and is_return != 1 and gst_category ='Unregistered' """.format(flt(b2c_limit))

		elif self.filters.get("type_of_business") ==  "B2C Small":
			conditions += """ and (
				SUBSTR(place_of_supply, 1, 2) = SUBSTR(company_gstin, 1, 2)
					or grand_total <= {0}) and is_return != 1 and gst_category ='Unregistered' """.format(flt(b2c_limit))

		elif self.filters.get("type_of_business") ==  "CDNR":
			conditions += """ and is_return = 1 """

		elif self.filters.get("type_of_business") ==  "EXPORT":
			conditions += """ and is_return !=1 and gst_category = 'Overseas' """
		return conditions

	def get_invoice_items(self):
		self.invoice_items = frappe._dict()
		self.item_tax_rate = frappe._dict()

		items = frappe.db.sql("""
			select item_code, parent, base_net_amount, item_tax_rate
			from `tab%s Item`
			where parent in (%s)
		""" % (self.doctype, ', '.join(['%s']*len(self.invoices))), tuple(self.invoices), as_dict=1)

		for d in items:
			if d.item_code not in self.invoice_items.get(d.parent, {}):
				self.invoice_items.setdefault(d.parent, {}).setdefault(d.item_code,
					sum(i.get('base_net_amount', 0) for i in items
						if i.item_code == d.item_code and i.parent == d.parent))

				item_tax_rate = {}

				if d.item_tax_rate:
					item_tax_rate = json.loads(d.item_tax_rate)

					for account, rate in item_tax_rate.items():
						tax_rate_dict = self.item_tax_rate.setdefault(d.parent, {}).setdefault(d.item_code, [])
						tax_rate_dict.append(rate)

	def get_items_based_on_tax_rate(self):
		self.tax_details = frappe.db.sql("""
			select
				parent, account_head, item_wise_tax_detail, base_tax_amount_after_discount_amount
			from `tab%s`
			where
				parenttype = %s and docstatus = 1
				and parent in (%s)
			order by account_head
		""" % (self.tax_doctype, '%s', ', '.join(['%s']*len(self.invoices.keys()))),
			tuple([self.doctype] + list(self.invoices.keys())))

		self.items_based_on_tax_rate = {}
		self.invoice_cess = frappe._dict()
		self.cgst_sgst_invoices = []

		unidentified_gst_accounts = []
		unidentified_gst_accounts_invoice = []
		for parent, account, item_wise_tax_detail, tax_amount in self.tax_details:
			if account in self.gst_accounts.cess_account:
				self.invoice_cess.setdefault(parent, tax_amount)
			else:
				if item_wise_tax_detail:
					try:
						item_wise_tax_detail = json.loads(item_wise_tax_detail)
						cgst_or_sgst = False
						if account in self.gst_accounts.cgst_account \
							or account in self.gst_accounts.sgst_account:
							cgst_or_sgst = True

						if not (cgst_or_sgst or account in self.gst_accounts.igst_account):
							if "gst" in account.lower() and account not in unidentified_gst_accounts:
								unidentified_gst_accounts.append(account)
								unidentified_gst_accounts_invoice.append(parent)
							continue

						for item_code, tax_amounts in item_wise_tax_detail.items():
							tax_rate = tax_amounts[0]
							if tax_rate:
								if cgst_or_sgst:
									tax_rate *= 2
									if parent not in self.cgst_sgst_invoices:
										self.cgst_sgst_invoices.append(parent)

								rate_based_dict = self.items_based_on_tax_rate\
									.setdefault(parent, {}).setdefault(tax_rate, [])
								if item_code not in rate_based_dict:
									rate_based_dict.append(item_code)
					except ValueError:
						continue
		if unidentified_gst_accounts:
			frappe.msgprint(_("Following accounts might be selected in GST Settings:")
				+ "<br>" + "<br>".join(unidentified_gst_accounts), alert=True)

		# Build itemised tax for export invoices where tax table is blank
		for invoice, items in iteritems(self.invoice_items):
			if invoice not in self.items_based_on_tax_rate and invoice not in unidentified_gst_accounts_invoice \
				and frappe.db.get_value(self.doctype, invoice, "export_type") == "Without Payment of Tax":
					self.items_based_on_tax_rate.setdefault(invoice, {}).setdefault(0, items.keys())

	def get_columns(self):
		self.tax_columns = [
			{
				"fieldname": "rate",
				"label": "Rate",
				"fieldtype": "Int",
				"width": 60
			},
			{
				"fieldname": "taxable_value",
				"label": "Taxable Value",
				"fieldtype": "Currency",
				"width": 100
			}
		]
		self.other_columns = []

		if self.filters.get("type_of_business") ==  "B2B":
			self.invoice_columns = [
				{
					"fieldname": "customer_gstin",
					"label": "GSTIN/UIN of Recipient",
					"fieldtype": "Data",
					"width": 150
				},
				{
					"fieldname": "customer_name",
					"label": "Receiver Name",
					"fieldtype": "Data",
					"width":100
				},
				{
					"fieldname": "invoice_number",
					"label": "Invoice Number",
					"fieldtype": "Link",
					"options": "Sales Invoice",
					"width":100
				},
				{
					"fieldname": "posting_date",
					"label": "Invoice date",
					"fieldtype": "Data",
					"width":80
				},
				{
					"fieldname": "invoice_value",
					"label": "Invoice Value",
					"fieldtype": "Currency",
					"width":100
				},
				{
					"fieldname": "place_of_supply",
					"label": "Place Of Supply",
					"fieldtype": "Data",
					"width":100
				},
				{
					"fieldname": "reverse_charge",
					"label": "Reverse Charge",
					"fieldtype": "Data"
				},
				{
					"fieldname": "gst_category",
					"label": "Invoice Type",
					"fieldtype": "Data"
				},
				{
					"fieldname": "ecommerce_gstin",
					"label": "E-Commerce GSTIN",
					"fieldtype": "Data",
					"width":120
				}
			]
			self.other_columns = [
					{
						"fieldname": "cess_amount",
						"label": "Cess Amount",
						"fieldtype": "Currency",
						"width": 100
					}
				]

		elif self.filters.get("type_of_business") ==  "B2C Large":
			self.invoice_columns = [
				{
					"fieldname": "invoice_number",
					"label": "Invoice Number",
					"fieldtype": "Link",
					"options": "Sales Invoice",
					"width": 120
				},
				{
					"fieldname": "posting_date",
					"label": "Invoice date",
					"fieldtype": "Data",
					"width": 100
				},
				{
					"fieldname": "invoice_value",
					"label": "Invoice Value",
					"fieldtype": "Currency",
					"width": 100
				},
				{
					"fieldname": "place_of_supply",
					"label": "Place Of Supply",
					"fieldtype": "Data",
					"width": 120
				},
				{
					"fieldname": "ecommerce_gstin",
					"label": "E-Commerce GSTIN",
					"fieldtype": "Data",
					"width": 130
				}
			]
			self.other_columns = [
					{
						"fieldname": "cess_amount",
						"label": "Cess Amount",
						"fieldtype": "Currency",
						"width": 100
					}
				]
		elif self.filters.get("type_of_business") ==  "CDNR":
			self.invoice_columns = [
				{
					"fieldname": "customer_gstin",
					"label": "GSTIN/UIN of Recipient",
					"fieldtype": "Data",
					"width": 150
				},
				{
					"fieldname": "customer_name",
					"label": "Receiver Name",
					"fieldtype": "Data",
					"width": 120
				},
				{
					"fieldname": "return_against",
					"label": "Invoice/Advance Receipt Number",
					"fieldtype": "Link",
					"options": "Sales Invoice",
					"width": 120
				},
				{
					"fieldname": "posting_date",
					"label": "Invoice/Advance Receipt date",
					"fieldtype": "Data",
					"width": 120
				},
				{
					"fieldname": "invoice_number",
					"label": "Invoice/Advance Receipt Number",
					"fieldtype": "Link",
					"options": "Sales Invoice",
					"width":120
				},
				{
					"fieldname": "reason_for_issuing_document",
					"label": "Reason For Issuing document",
					"fieldtype": "Data",
					"width": 140
				},
				{
					"fieldname": "place_of_supply",
					"label": "Place Of Supply",
					"fieldtype": "Data",
					"width": 120
				},
				{
					"fieldname": "invoice_value",
					"label": "Invoice Value",
					"fieldtype": "Currency",
					"width": 120
				}
			]
			self.other_columns = [
				{
						"fieldname": "cess_amount",
						"label": "Cess Amount",
						"fieldtype": "Currency",
						"width": 100
				},
				{
					"fieldname": "pre_gst",
					"label": "PRE GST",
					"fieldtype": "Data",
					"width": 80
				},
				{
					"fieldname": "document_type",
					"label": "Document Type",
					"fieldtype": "Data",
					"width": 80
				}
			]
		elif self.filters.get("type_of_business") ==  "B2C Small":
			self.invoice_columns = [
				{
					"fieldname": "place_of_supply",
					"label": "Place Of Supply",
					"fieldtype": "Data",
					"width": 120
				},
				{
					"fieldname": "ecommerce_gstin",
					"label": "E-Commerce GSTIN",
					"fieldtype": "Data",
					"width": 130
				}
			]
			self.other_columns = [
				{
						"fieldname": "cess_amount",
						"label": "Cess Amount",
						"fieldtype": "Currency",
						"width": 100
				},
				{
					"fieldname": "type",
					"label": "Type",
					"fieldtype": "Data",
					"width": 50
				}
			]
		elif self.filters.get("type_of_business") ==  "EXPORT":
			self.invoice_columns = [
				{
					"fieldname": "export_type",
					"label": "Export Type",
					"fieldtype": "Data",
					"width":120
				},
				{
					"fieldname": "invoice_number",
					"label": "Invoice Number",
					"fieldtype": "Link",
					"options": "Sales Invoice",
					"width":120
				},
				{
					"fieldname": "posting_date",
					"label": "Invoice date",
					"fieldtype": "Data",
					"width": 120
				},
				{
					"fieldname": "invoice_value",
					"label": "Invoice Value",
					"fieldtype": "Currency",
					"width": 120
				},
				{
					"fieldname": "port_code",
					"label": "Port Code",
					"fieldtype": "Data",
					"width": 120
				},
				{
					"fieldname": "shipping_bill_number",
					"label": "Shipping Bill Number",
					"fieldtype": "Data",
					"width": 120
				},
				{
					"fieldname": "shipping_bill_date",
					"label": "Shipping Bill Date",
					"fieldtype": "Data",
					"width": 120
				}
			]
		self.columns = self.invoice_columns + self.tax_columns + self.other_columns

@frappe.whitelist()
def get_json(filters, report_name, data):
	filters = json.loads(filters)
	report_data = json.loads(data)
	gstin = get_company_gstin_number(filters["company"])

	fp = "%02d%s" % (getdate(filters["to_date"]).month, getdate(filters["to_date"]).year)

	gst_json = {"gstin": "", "version": "GST2.2.9",
		"hash": "hash", "gstin": gstin, "fp": fp}

	res = {}
	if filters["type_of_business"] == "B2B":
		for item in report_data[:-1]:
			res.setdefault(item["customer_gstin"], {}).setdefault(item["invoice_number"],[]).append(item)

		out = get_b2b_json(res, gstin)
		gst_json["b2b"] = out

	elif filters["type_of_business"] == "B2C Large":
		for item in report_data[:-1]:
			res.setdefault(item["place_of_supply"], []).append(item)

		out = get_b2cl_json(res, gstin)
		gst_json["b2cl"] = out

	elif filters["type_of_business"] == "B2C Small":
		out = get_b2cs_json(report_data[:-1], gstin)
		gst_json["b2cs"] = out

	elif filters["type_of_business"] == "EXPORT":
		for item in report_data[:-1]:
			res.setdefault(item["export_type"], []).append(item)

		out = get_export_json(res)
		gst_json["exp"] = out

	return {
		'report_name': report_name,
		'report_type': filters['type_of_business'],
		'data': gst_json
	}

def get_b2b_json(res, gstin):
	inv_type, out = {"Registered Regular": "R", "Deemed Export": "DE", "URD": "URD", "SEZ": "SEZ"}, []
	for gst_in in res:
		b2b_item, inv = {"ctin": gst_in, "inv": []}, []
		if not gst_in: continue

		for number, invoice in iteritems(res[gst_in]):
			if not invoice[0]["place_of_supply"]:
				frappe.throw(_("""{0} not entered in Invoice {1}.
					Please update and try again""").format(frappe.bold("Place Of Supply"),
					frappe.bold(invoice[0]['invoice_number'])))

			inv_item = get_basic_invoice_detail(invoice[0])
			inv_item["pos"] = "%02d" % int(invoice[0]["place_of_supply"].split('-')[0])
			inv_item["rchrg"] = invoice[0]["reverse_charge"]
			inv_item["inv_typ"] = inv_type.get(invoice[0].get("gst_category", ""),"")

			if inv_item["pos"]=="00": continue
			inv_item["itms"] = []

			for item in invoice:
				inv_item["itms"].append(get_rate_and_tax_details(item, gstin))

			inv.append(inv_item)

		if not inv: continue
		b2b_item["inv"] = inv
		out.append(b2b_item)

	return out

def get_b2cs_json(data, gstin):

	company_state_number = gstin[0:2]

	out = []
	for d in data:
		if not d.get("place_of_supply"):
			frappe.throw(_("""{0} not entered in some invoices.
				Please update and try again""").format(frappe.bold("Place Of Supply")))

		pos = d.get('place_of_supply').split('-')[0]
		tax_details = {}

		rate = d.get('rate', 0)
		tax = flt((d["taxable_value"]*rate)/100.0, 2)

		if company_state_number == pos:
			tax_details.update({"camt": flt(tax/2.0, 2), "samt": flt(tax/2.0, 2)})
		else:
			tax_details.update({"iamt": tax})

		inv = {
			"sply_ty": "INTRA" if company_state_number == pos else "INTER",
			"pos": pos,
			"typ": d.get('type'),
			"txval": flt(d.get('taxable_value'), 2),
			"rt": rate,
			"iamt": flt(tax_details.get('iamt'), 2),
			"camt": flt(tax_details.get('camt'), 2),
			"samt": flt(tax_details.get('samt'), 2),
			"csamt": flt(d.get('cess_amount'), 2)
		}

		if d.get('type') == "E" and d.get('ecommerce_gstin'):
			inv.update({
				"etin": d.get('ecommerce_gstin')
			})

		out.append(inv)

	return out

def get_b2cl_json(res, gstin):
	out = []
	for pos in res:
		if not pos:
			frappe.throw(_("""{0} not entered in some invoices.
				Please update and try again""").format(frappe.bold("Place Of Supply")))

		b2cl_item, inv = {"pos": "%02d" % int(pos.split('-')[0]), "inv": []}, []

		for row in res[pos]:
			inv_item = get_basic_invoice_detail(row)
			if row.get("sale_from_bonded_wh"):
				inv_item["inv_typ"] = "CBW"

			inv_item["itms"] = [get_rate_and_tax_details(row, gstin)]

			inv.append(inv_item)

		b2cl_item["inv"] = inv
		out.append(b2cl_item)

	return out

def get_export_json(res):
	out = []
	for exp_type in res:
		exp_item, inv = {"exp_typ": exp_type, "inv": []}, []

		for row in res[exp_type]:
			inv_item = get_basic_invoice_detail(row)
			inv_item["itms"] = [{
				"txval": flt(row["taxable_value"], 2),
				"rt": row["rate"] or 0,
				"iamt": 0,
				"csamt": 0
			}]

			inv.append(inv_item)

		exp_item["inv"] = inv
		out.append(exp_item)

	return out

def get_basic_invoice_detail(row):
	return {
		"inum": row["invoice_number"],
		"idt": getdate(row["posting_date"]).strftime('%d-%m-%Y'),
		"val": flt(row["invoice_value"], 2)
	}

def get_rate_and_tax_details(row, gstin):
	itm_det = {"txval": flt(row["taxable_value"], 2),
		"rt": row["rate"],
		"csamt": (flt(row.get("cess_amount"), 2) or 0)
	}

	# calculate rate
	num = 1 if not row["rate"] else "%d%02d" % (row["rate"], 1)
	rate = row.get("rate") or 0

	# calculate tax amount added
	tax = flt((row["taxable_value"]*rate)/100.0, 2)
	frappe.errprint([tax, tax/2])
	if row.get("customer_gstin") and gstin[0:2] == row["customer_gstin"][0:2]:
		itm_det.update({"camt": flt(tax/2.0, 2), "samt": flt(tax/2.0, 2)})
	else:
		itm_det.update({"iamt": tax})

	return {"num": int(num), "itm_det": itm_det}

def get_company_gstin_number(company):
	filters = [
		["is_your_company_address", "=", 1],
		["Dynamic Link", "link_doctype", "=", "Company"],
		["Dynamic Link", "link_name", "=", company],
		["Dynamic Link", "parenttype", "=", "Address"],
	]

	gstin = frappe.get_all("Address", filters=filters, fields=["gstin"])

	if gstin:
		return gstin[0]["gstin"]
	else:
		frappe.throw(_("Please set valid GSTIN No. in Company Address for company {0}").format(
			frappe.bold(company)
		))

@frappe.whitelist()
def download_json_file():
	''' download json content in a file '''
	data = frappe._dict(frappe.local.form_dict)
	frappe.response['filename'] = frappe.scrub("{0} {1}".format(data['report_name'], data['report_type'])) + '.json'
	frappe.response['filecontent'] = data['data']
	frappe.response['content_type'] = 'application/json'
	frappe.response['type'] = 'download'
