# Copyright (c) 2015, Frappe Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe import _, scrub
from frappe.utils import getdate, nowdate, flt, cint, formatdate, cstr
from frappe.desk.query_report import group_report_data
from erpnext.accounts.utils import get_allow_cost_center_in_entry_of_bs_account

class ReceivablePayableReport(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.filters.report_date = getdate(self.filters.report_date or nowdate())
		self.age_as_on = getdate(nowdate()) \
			if self.filters.report_date > getdate(nowdate()) \
			else self.filters.report_date

	def run(self, args):
		party_naming_by = frappe.db.get_value(args.get("naming_by")[0], None, args.get("naming_by")[1])
		columns = self.get_columns(party_naming_by, args)
		data = self.get_data(party_naming_by, args)
		data_out = self.get_grouped_data(columns, data)
		chart = self.get_chart_data(columns, data)

		return columns, data_out, None, chart

	def get_columns(self, party_naming_by, args):
		columns = [
			{
				"label": _("Posting Date"),
				"fieldtype": "Date",
				"fieldname": "posting_date",
				"width": 80
			},
			{
				"label": _(args.get("party_type")),
				"fieldtype": "Link",
				"fieldname": "party",
				"options": args.get("party_type"),
				"width": 200 if self.filters.get("group_by", "Ungrouped") == "Ungrouped" else 300
			}
		]

		if self.filters.get("group_by", "Ungrouped") != "Ungrouped":
			columns = list(reversed(columns))

		if party_naming_by == "Naming Series":
			columns.append({
				"label": _(args.get("party_type") + " Name"),
				"fieldtype": "Link",
				"fieldname": "party_name",
				"options": args.get("party_type"),
				"width": 110
			})

		columns += [
			{
				"label": _("Voucher Type"),
				"fieldtype": "Data",
				"fieldname": "voucher_type",
				"width": 110
			},
			{
				"label": _("Voucher No"),
				"fieldtype": "Dynamic Link",
				"fieldname": "voucher_no",
				"width": 150,
				"options": "voucher_type",
			},
			{
				"label": _("Due Date"),
				"fieldtype": "Date",
				"fieldname": "due_date",
				"width": 80,
			}
		]

		if args.get("party_type") == "Supplier":
			columns += [
				{
					"label": _("Bill No"),
					"fieldtype": "Data",
					"fieldname": "bill_no",
					"width": 80
				},
				{
					"label": _("Bill Date"),
					"fieldtype": "Date",
					"fieldname": "bill_date",
					"width": 80,
				}
			]

		if self.filters.based_on_payment_terms:
			columns.append({
				"label": _("Payment Term"),
				"fieldname": "payment_term",
				"fieldtype": "Data",
				"width": 120
			})
			columns.append({
				"label": _("Invoice Grand Total"),
				"fieldname": "invoice_grand_total",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120
			})

		credit_or_debit_note = "Credit Note" if args.get("party_type") == "Customer" else "Debit Note"
		columns += [
			{
				"label": _("Invoiced Amount"),
				"fieldname": "invoiced_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120
			},
			{
				"label": _("Paid Amount"),
				"fieldname": "paid_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120
			},
			{
				"label": _(credit_or_debit_note),
				"fieldname": "return_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120
			},
			{
				"label": _("Outstanding Amount"),
				"fieldname": "outstanding_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120
			}
		]

		columns.append({
			"label": _("Age (Days)"),
			"fieldtype": "Int",
			"fieldname": "age",
			"width": 80,
		})

		self.ageing_col_idx_start = len(columns)

		if not "range1" in self.filters:
			self.filters["range1"] = "30"
		if not "range2" in self.filters:
			self.filters["range2"] = "60"
		if not "range3" in self.filters:
			self.filters["range3"] = "90"
		if not "range4" in self.filters:
			self.filters["range4"] = "120"

		for i, label in enumerate(["0-{range1}".format(range1=self.filters["range1"]),
			"{range1}-{range2}".format(range1=cint(self.filters["range1"])+ 1, range2=self.filters["range2"]),
			"{range2}-{range3}".format(range2=cint(self.filters["range2"])+ 1, range3=self.filters["range3"]),
			"{range3}-{range4}".format(range3=cint(self.filters["range3"])+ 1, range4=self.filters["range4"]),
			"{range4}-{above}".format(range4=cint(self.filters["range4"])+ 1, above=_("Above"))]):
				columns.append({
					"label": label,
					"fieldname": "range{}".format(i+1),
					"fieldtype": "Currency",
					"options": "currency",
					"width": 120
				})

		columns += [
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"width": 50
		},
		{
			"fieldname": "pdc/lc_ref",
			"label": _("PDC/LC Ref"),
			"fieldtype": "Data",
			"width": 110
		},
		{
			"fieldname": "pdc/lc_amount",
			"label": _("PDC/LC Amount"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 130
		},
		{
			"fieldname": "remaining_balance",
			"label": _("Remaining Balance"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 130
		}]

		if args.get('party_type') == 'Customer':
			columns += [
				{
					"label": _("Customer LPO"),
					"fieldtype": "Data",
					"fieldname": "po_no",
					"width": 100,
				},
				{
					"fieldname": "delivery_note",
					"label": _("Delivery Note"),
					"fieldtype": "Link",
					"options": "Delivery Note",
					"width": 100
				},
				{
					"fieldname": "territory",
					"label": _("Territory"),
					"fieldtype": "Link",
					"options": "Territory",
					"width": 80
				},
				{
					"fieldname": "customer_group",
					"label": _("Customer Group"),
					"fieldtype": "Link",
					"options": "Customer Group",
					"width": 120
				},
				{
					"label": _("Sales Person"),
					"fieldtype": "Data",
					"fieldname": "sales_person",
					"width": 120,
				}
			]
		if args.get("party_type") == "Supplier":
			columns += [
				{
					"fieldname": "supplier_group",
					"label": _("Supplier Group"),
					"fieldtype": "Link",
					"options": "Supplier Group",
					"width": 120
				}
			]

		if get_allow_cost_center_in_entry_of_bs_account():
			columns.append({
				"label": _("Cost Center"),
				"fieldtype": "Link",
				"fieldname": "cost_center",
				"options": "Cost Center",
				"width": 100
			})

		if args.get("party_type") == 'Customer':
			columns.append({
				"label": _("Customer Contact"),
				"fieldtype": "Link",
				"fieldname": "contact",
				"options": "Contact",
				"width": 130
			})

		columns.append({
			"fieldname": "remarks",
			"label": _("Remarks"),
			"fieldtype": "Data",
			"width": 200
		})

		return columns

	def get_data(self, party_naming_by, args):
		from erpnext.accounts.utils import get_currency_precision
		self.currency_precision = get_currency_precision() or 2
		self.dr_or_cr = "debit" if args.get("party_type") == "Customer" else "credit"

		future_vouchers = self.get_entries_after(self.filters.report_date, args.get("party_type"))

		if not self.filters.get("company"):
			self.filters["company"] = frappe.db.get_single_value('Global Defaults', 'default_company')

		self.company_currency = frappe.get_cached_value('Company',  self.filters.get("company"), "default_currency")

		return_entries = self.get_return_entries(args.get("party_type"))

		data = []
		self.pdc_details = get_pdc_details(args.get("party_type"), self.filters.report_date)
		gl_entries_data = self.get_entries_till(self.filters.report_date, args.get("party_type"))

		if gl_entries_data:
			voucher_nos = [d.voucher_no for d in gl_entries_data] or []
			dn_details = get_dn_details(args.get("party_type"), voucher_nos)
			self.voucher_details = get_voucher_details(args.get("party_type"), voucher_nos, dn_details)

		if self.filters.based_on_payment_terms and gl_entries_data:
			self.payment_term_map = self.get_payment_term_detail(voucher_nos)

		for gle in gl_entries_data:
			if self.is_receivable_or_payable(gle, self.dr_or_cr, future_vouchers, return_entries) and self.is_in_cost_center(gle):
				outstanding_amount, credit_note_amount, payment_amount = self.get_outstanding_amount(
					gle, self.filters.report_date, self.dr_or_cr, return_entries)

				temp_outstanding_amt = outstanding_amount
				temp_credit_note_amt = credit_note_amount

				if abs(outstanding_amount) > 0.1/10**self.currency_precision:
					if self.filters.based_on_payment_terms and self.payment_term_map.get(gle.voucher_no):
						for d in self.payment_term_map.get(gle.voucher_no):
							# Allocate payment amount based on payment terms(FIFO order)
							payment_amount, d.payment_amount = self.allocate_based_on_fifo(payment_amount, d.payment_term_amount)

							term_outstanding_amount = d.payment_term_amount - d.payment_amount

							# Allocate credit note based on payment terms(FIFO order)
							credit_note_amount, d.credit_note_amount = self.allocate_based_on_fifo(credit_note_amount, term_outstanding_amount)

							term_outstanding_amount -= d.credit_note_amount

							row_outstanding = term_outstanding_amount
							# Allocate PDC based on payment terms(FIFO order)
							d.pdc_details, d.pdc_amount = self.allocate_pdc_amount_in_fifo(gle, row_outstanding)

							if term_outstanding_amount > 0:
								row = self.prepare_row(party_naming_by, args, gle, term_outstanding_amount,
									d.credit_note_amount, d.due_date, d.payment_amount , d.payment_term_amount,
									d.description, d.pdc_amount, d.pdc_details)
								data.append(row)

						if credit_note_amount:
							row = self.prepare_row_without_payment_terms(party_naming_by, args, gle, temp_outstanding_amt,
								temp_credit_note_amt)
							data.append(row)

					else:
						row = self.prepare_row_without_payment_terms(party_naming_by, args, gle, outstanding_amount,
							credit_note_amount)
						data.append(row)
		return data

	def get_grouped_data(self, columns, data):
		level1 = self.filters.get("group_by", "").replace("Group by ", "")
		level2 = self.filters.get("group_by_2", "").replace("Group by ", "")
		level1_fieldname = "party" if level1 in ['Customer', 'Supplier'] else scrub(level1)
		level2_fieldname = "party" if level2 in ['Customer', 'Supplier'] else scrub(level2)

		group_by = [None]
		group_by_labels = {}
		if level1 and level1 != "Ungrouped":
			group_by.append(level1_fieldname)
			group_by_labels[level1_fieldname] = level1
		if level2 and level2 != "Ungrouped":
			group_by.append(level2_fieldname)
			group_by_labels[level2_fieldname] = level2

		if len(group_by) <= 1:
			return self.group_aggregate_age(data, columns)

		total_fields = [c['fieldname'] for c in columns
			if c['fieldtype'] in ['Float', 'Currency', 'Int'] and c['fieldname'] != 'age']

		def postprocess_group(group_object, grouped_by):
			group_object.totals['party'] = "'Total'" if not group_object.group_field else\
				"'{0}: {1}'".format(group_object.group_label, group_object.group_value)

			if group_object.group_field == 'party':
				group_object.totals['currency'] = group_object.rows[0].get("currency")

				group_object.tax_id = self.party_map.get(group_object.group_value, {}).get("tax_id")
				group_object.payment_terms = self.party_map.get(group_object.group_value, {}).get("payment_terms")
				group_object.credit_limit = self.party_map.get(group_object.group_value, {}).get("credit_limit")

			group_object.rows = self.group_aggregate_age(group_object.rows, columns, grouped_by)

		return group_report_data(data, group_by, total_fields=total_fields, postprocess_group=postprocess_group,
			group_by_labels=group_by_labels)

	def group_aggregate_age(self, data, columns, grouped_by=None):
		if not self.filters.from_age:
			return data

		to_group = []
		to_keep = []

		for d in data:
			if d._isGroupTotal or d._isGroup or d.age >= cint(self.filters.from_age):
				to_keep.append(d)
			else:
				to_group.append(d)

		if not to_group:
			return data

		total_fields = [c['fieldname'] for c in columns
			if c['fieldtype'] in ['Float', 'Currency', 'Int'] and c['fieldname'] != 'age']

		below_age_total = group_report_data(to_group, None, total_fields=total_fields, totals_only=True)
		below_age_total = below_age_total[0]
		above_age_total = group_report_data(to_keep, None, total_fields=total_fields, totals_only=True)
		above_age_total = above_age_total[0] if above_age_total else {}

		if grouped_by:
			below_age_total.update(grouped_by)
			above_age_total.update(grouped_by)

		below_age_total['voucher_type'] = _("Age <= {0} Total").format(self.filters.from_age)

		above_age_total['voucher_type'] = _("Age > {0} Total").format(self.filters.from_age)
		above_age_total['_excludeFromTotal'] = True
		above_age_total['_bold'] = True

		res = []
		if to_keep:
			res += to_keep + [above_age_total, {}]
		res.append(below_age_total)

		return res

	def allocate_pdc_amount_in_fifo(self, gle, row_outstanding):
		pdc_list = self.pdc_details.get((gle.voucher_no, gle.party), [])

		pdc_details = []
		pdc_amount = 0
		for pdc in pdc_list:
			if row_outstanding <= pdc.pdc_amount:
				pdc_amount += row_outstanding
				pdc.pdc_amount -= row_outstanding
				if row_outstanding and pdc.pdc_ref and pdc.pdc_date:
					pdc_details.append(cstr(pdc.pdc_ref) + "/" + formatdate(pdc.pdc_date))
				row_outstanding = 0

			else:
				pdc_amount = pdc.pdc_amount
				if pdc.pdc_amount and pdc.pdc_ref and pdc.pdc_date:
					pdc_details.append(cstr(pdc.pdc_ref) + "/" + formatdate(pdc.pdc_date))
				pdc.pdc_amount = 0
				row_outstanding -= pdc_amount

		return pdc_details, pdc_amount

	def prepare_row_without_payment_terms(self, party_naming_by, args, gle, outstanding_amount, credit_note_amount):
		pdc_list = self.pdc_details.get((gle.voucher_no, gle.party), [])
		pdc_amount = 0
		pdc_details = []
		for d in pdc_list:
			pdc_amount += flt(d.pdc_amount)
			if pdc_amount and d.pdc_ref and d.pdc_date:
				pdc_details.append(cstr(d.pdc_ref) + "/" + formatdate(d.pdc_date))

		row = self.prepare_row(party_naming_by, args, gle, outstanding_amount,
			credit_note_amount, pdc_amount=pdc_amount, pdc_details=pdc_details)

		return row


	def allocate_based_on_fifo(self, total_amount, row_amount):
		allocated_amount = 0
		if row_amount <= total_amount:
			allocated_amount = row_amount
			total_amount -= row_amount
		else:
			allocated_amount = total_amount
			total_amount = 0

		return total_amount, allocated_amount

	def prepare_row(self, party_naming_by, args, gle, outstanding_amount, credit_note_amount,
		due_date=None, paid_amt=None, payment_term_amount=None, payment_term=None, pdc_amount=None, pdc_details=None):
		row = frappe._dict({"posting_date": gle.posting_date, "party": gle.party})

		# customer / supplier name
		if party_naming_by == "Naming Series":
			row["party_name"] = self.get_party_name(gle.party_type, gle.party)

		if args.get("party_type") == 'Customer':
			row["contact"] = self.get_customer_contact(gle.party_type, gle.party)

		# get due date
		if not due_date:
			due_date = self.voucher_details.get(gle.voucher_no, {}).get("due_date", "")
		bill_date = self.voucher_details.get(gle.voucher_no, {}).get("bill_date", "")

		row["voucher_type"] = gle.voucher_type
		row["voucher_no"] = gle.voucher_no
		row["due_date"] = due_date

		row["cost_center"] = gle.cost_center

		# get supplier bill details
		if args.get("party_type") == "Supplier":
			row["bill_no"] = self.voucher_details.get(gle.voucher_no, {}).get("bill_no", "")
			row["bill_date"] = self.voucher_details.get(gle.voucher_no, {}).get("bill_date", "")

		# invoiced and paid amounts
		invoiced_amount = gle.get(self.dr_or_cr) if (gle.get(self.dr_or_cr) > 0) else 0

		if self.filters.based_on_payment_terms:
			row["payment_term"] = payment_term
			row["invoice_grand_total"] = invoiced_amount
			if payment_term_amount:
				invoiced_amount = payment_term_amount

		if not payment_term_amount:
			paid_amt = invoiced_amount - outstanding_amount - credit_note_amount

		row["invoiced_amount"] = invoiced_amount
		row["paid_amount"] = paid_amt
		row["return_amount"] = credit_note_amount
		row["outstanding_amount"] = outstanding_amount

		# ageing data
		if self.filters.ageing_based_on == "Due Date":
			entry_date = due_date
		elif self.filters.ageing_based_on == "Supplier Invoice Date":
			entry_date = bill_date
		else:
			entry_date = gle.posting_date

		ageing_data = get_ageing_data(cint(self.filters.range1), cint(self.filters.range2),
			cint(self.filters.range3), cint(self.filters.range4), self.age_as_on, entry_date, outstanding_amount)
		row["age"] = ageing_data[0]
		for i in range(5):
			row["range{}".format(i+1)] = ageing_data[i+1]

		# issue 6371-Ageing buckets should not have amounts if due date is not reached
		if self.filters.ageing_based_on == "Due Date" \
				and getdate(due_date) > getdate(self.filters.report_date):
			for i in range(5):
				row["range{}".format(i+1)] = 0

		if self.filters.ageing_based_on == "Supplier Invoice Date" \
				and getdate(bill_date) > getdate(self.filters.report_date):
			for i in range(5):
				row["range{}".format(i+1)] = 0

		if self.filters.get(scrub(args.get("party_type"))):
			row["currency"] = gle.account_currency
		else:
			row["currency"] = self.company_currency

		remaining_balance = outstanding_amount - flt(pdc_amount)
		pdc_details = ", ".join(pdc_details)

		row["pdc/lc_ref"] = pdc_details
		row["pdc/lc_amount"] = pdc_amount
		row["remaining_balance"] = remaining_balance

		if args.get('party_type') == 'Customer':
			# customer LPO
			row["po_no"] = self.voucher_details.get(gle.voucher_no, {}).get("po_no")

			# Delivery Note
			row["delivery_note"] = self.voucher_details.get(gle.voucher_no, {}).get("delivery_note")

		# customer territory / supplier group
		if args.get("party_type") == "Customer":
			row["territory"] = self.get_territory(gle.party)
			row["customer_group"] = self.get_customer_group(gle.party)
			row["sales_person"] = self.get_sales_person(gle.voucher_no, gle.against_voucher, gle.party)
		if args.get("party_type") == "Supplier":
			row["supplier_group"] = self.get_supplier_group(gle.party)

		row["remarks"] = gle.remarks

		return row

	def get_entries_after(self, report_date, party_type):
		# returns a distinct list
		return list(set([(e.voucher_type, e.voucher_no) for e in self.get_gl_entries(party_type, report_date, for_future=True)]))

	def get_entries_till(self, report_date, party_type):
		# returns a generator
		return self.get_gl_entries(party_type, report_date)

	@staticmethod
	def is_receivable_or_payable(gle, dr_or_cr, future_vouchers, return_entries):
		return (
			# advance
			(not gle.against_voucher) or

			# against sales order/purchase order
			(gle.against_voucher_type in ["Sales Order", "Purchase Order"]) or

			# sales invoice/purchase invoice
			(gle.against_voucher==gle.voucher_no and gle.get(dr_or_cr) > 0) or

			# standalone credit notes
			(gle.against_voucher==gle.voucher_no and gle.voucher_no in return_entries and not return_entries.get(gle.voucher_no)) or

			# entries adjusted with future vouchers
			((gle.against_voucher_type, gle.against_voucher) in future_vouchers)
		)

	def is_in_cost_center(self, gle):
		if self.filters.get("cost_center"):
			if gle.get("cost_center_lft") and gle.get("cost_center_rgt"):
				if not self.filters.get("cost_center_lft") or not self.filters.get("cost_center_rgt"):
					self.filters["cost_center_lft"], self.filters["cost_center_rgt"] = frappe.get_value("Cost Center",
						self.filters.get("cost_center"), ["lft", "rgt"])

				return gle.cost_center_lft >= self.filters.cost_center_lft and gle.cost_center_rgt <= self.filters.cost_center_rgt
			else:
				return False
		else:
			return True

	def get_return_entries(self, party_type):
		doctype = "Sales Invoice" if party_type == "Customer" else "Purchase Invoice"
		return_entries = frappe._dict(frappe.get_all(doctype,
			filters={"is_return": 1, "docstatus": 1}, fields=["name", "return_against"], as_list=1))
		return return_entries

	def get_outstanding_amount(self, gle, report_date, dr_or_cr, return_entries):
		payment_amount, credit_note_amount = 0.0, 0.0
		reverse_dr_or_cr = "credit" if dr_or_cr=="debit" else "debit"

		for e in self.get_gl_entries_for(gle.party, gle.party_type, gle.voucher_type, gle.voucher_no):
			if getdate(e.posting_date) <= report_date and e.name!=gle.name:
				amount = flt(e.get(reverse_dr_or_cr), self.currency_precision) - flt(e.get(dr_or_cr), self.currency_precision)
				if e.voucher_no not in return_entries:
					payment_amount += amount
				else:
					credit_note_amount += amount

		# for stand alone credit/debit note
		if gle.voucher_no in return_entries and flt(gle.get(reverse_dr_or_cr)) - flt(gle.get(dr_or_cr) > 0):
			amount = flt(gle.get(reverse_dr_or_cr), self.currency_precision) - flt(gle.get(dr_or_cr), self.currency_precision)
			credit_note_amount += amount
			payment_amount -= amount

		outstanding_amount = (flt((flt(gle.get(dr_or_cr), self.currency_precision)
			- flt(gle.get(reverse_dr_or_cr), self.currency_precision)
			- payment_amount - credit_note_amount), self.currency_precision))

		credit_note_amount = flt(credit_note_amount, self.currency_precision)

		return outstanding_amount, credit_note_amount, payment_amount

	def get_party_name(self, party_type, party_name):
		return self.get_party_map(party_type).get(party_name, {}).get("customer_name" if party_type == "Customer" else "supplier_name") or ""

	def get_customer_contact(self, party_type, party_name):
		return self.get_party_map(party_type).get(party_name, {}).get("customer_primary_contact")

	def get_territory(self, party_name):
		return self.get_party_map("Customer").get(party_name, {}).get("territory")

	def get_sales_person(self, voucher_no, against_voucher, party_name):
		return self.voucher_details.get(voucher_no, {}).get("sales_person")\
			or self.voucher_details.get(against_voucher, {}).get("sales_person")\
			or self.get_party_map("Customer").get(party_name, {}).get("sales_person")

	def get_customer_group(self, party_name):
		return self.get_party_map("Customer").get(party_name, {}).get("customer_group")

	def get_supplier_group(self, party_name):
		return self.get_party_map("Supplier").get(party_name, {}).get("supplier_group")

	def get_party_map(self, party_type):
		if not hasattr(self, "party_map"):
			if party_type == "Customer":
				party_data = frappe.db.sql("""
					select
						p.name, p.customer_name, p.territory, p.customer_group, p.customer_primary_contact,
						GROUP_CONCAT(steam.sales_person SEPARATOR ', ') as sales_person,
						p.payment_terms, p.credit_limit, p.tax_id
					from `tabCustomer` p
					left join `tabSales Team` steam on steam.parent = p.name and steam.parenttype = 'Customer'
					group by p.name
				""", as_dict=True)
			elif party_type == "Supplier":
				party_data = frappe.db.sql("""
					select p.name, p.supplier_name, p.supplier_group, p.tax_id, p.payment_terms
					from `tabSupplier` p
				""", as_dict=True)
			else:
				party_data = []

			self.party_map = dict([(r.name, r) for r in party_data])

		return self.party_map

	def get_gl_entries(self, party_type, date=None, for_future=False):
		conditions, values = self.prepare_conditions(party_type)

		if self.filters.get(scrub(party_type)):
			select_fields = "sum(gle.debit_in_account_currency) as debit, sum(gle.credit_in_account_currency) as credit"
		else:
			select_fields = "sum(gle.debit) as debit, sum(gle.credit) as credit"

		if self.filters.get("cost_center"):
			cost_center_fields = ", cc.lft as cost_center_lft, cc.rgt as cost_center_rgt"
			cost_center_join = "left join `tabCost Center` cc on cc.name = gle.cost_center"
		else:
			cost_center_fields = cost_center_join = ""

		if date and not for_future:
			conditions += " and gle.posting_date <= '%s'" % date

		if date and for_future:
			conditions += " and gle.posting_date > '%s'" % date

		self.gl_entries = frappe.db.sql("""
			select
				gle.name, gle.posting_date, gle.account, gle.party_type, gle.party, gle.voucher_type, gle.voucher_no,
				gle.against_voucher_type, gle.against_voucher, gle.account_currency, gle.remarks, gle.cost_center,
				{select_fields} {cost_center_fields}
			from
				`tabGL Entry` gle {cost_center_join}
			where
				gle.docstatus < 2 and gle.party_type=%s and (gle.party is not null and gle.party != '') {conditions}
				group by gle.voucher_type, gle.voucher_no, gle.against_voucher_type, gle.against_voucher, gle.party
				order by gle.posting_date, gle.party""".format(  # nosec
			select_fields=select_fields,
			cost_center_fields=cost_center_fields,
			cost_center_join=cost_center_join,
			conditions=conditions), values, as_dict=True)

		return self.gl_entries

	def prepare_conditions(self, party_type):
		conditions = [""]
		values = [party_type]

		party_type_field = scrub(party_type)

		if self.filters.company:
			conditions.append("gle.company=%s")
			values.append(self.filters.company)

		if self.filters.finance_book:
			conditions.append("ifnull(gle.finance_book,'') in (%s, '')")
			values.append(self.filters.finance_book)

		if self.filters.get(party_type_field):
			conditions.append("gle.party=%s")
			values.append(self.filters.get(party_type_field))

		if party_type_field=="customer":
			account_type = "Receivable"
			if self.filters.get("customer_group"):
				lft, rgt = frappe.db.get_value("Customer Group",
					self.filters.get("customer_group"), ["lft", "rgt"])

				conditions.append("""gle.party in (select name from tabCustomer
					where exists(select name from `tabCustomer Group` where lft >= {0} and rgt <= {1}
						and name=tabCustomer.customer_group))""".format(lft, rgt))

			if self.filters.get("territory"):
				lft, rgt = frappe.db.get_value("Territory",
					self.filters.get("territory"), ["lft", "rgt"])

				conditions.append("""gle.party in (select name from tabCustomer
					where exists(select name from `tabTerritory` where lft >= {0} and rgt <= {1}
						and name=tabCustomer.territory))""".format(lft, rgt))

			if self.filters.get("payment_terms_template"):
				conditions.append("gle.party in (select name from tabCustomer where payment_terms=%s)")
				values.append(self.filters.get("payment_terms_template"))

			if self.filters.get("sales_partner"):
				conditions.append("gle.party in (select name from tabCustomer where default_sales_partner=%s)")
				values.append(self.filters.get("sales_partner"))

			if self.filters.get("sales_person"):
				lft, rgt = frappe.db.get_value("Sales Person",
					self.filters.get("sales_person"), ["lft", "rgt"])

				conditions.append("""exists(select name from `tabSales Team` steam where
					steam.sales_person in (select name from `tabSales Person` where lft >= {0} and rgt <= {1})
					and ((steam.parent = voucher_no and steam.parenttype = voucher_type)
						or (steam.parent = against_voucher and steam.parenttype = against_voucher_type)))""".format(lft, rgt))

		elif party_type_field=="supplier":
			account_type = "Payable"
			if self.filters.get("supplier_group"):
				conditions.append("""gle.party in (select name from tabSupplier
					where supplier_group=%s)""")
				values.append(self.filters.get("supplier_group"))

		accounts = [d.name for d in frappe.get_all("Account",
			filters={"account_type": account_type, "company": self.filters.company})]
		conditions.append("gle.account in (%s)" % ','.join(['%s'] *len(accounts)))
		values += accounts

		return " and ".join(conditions), values

	def get_gl_entries_for(self, party, party_type, against_voucher_type, against_voucher):
		if not hasattr(self, "gl_entries_map"):
			self.gl_entries_map = {}
			for gle in self.get_gl_entries(party_type):
				if gle.against_voucher_type and gle.against_voucher:
					self.gl_entries_map.setdefault(gle.party, {})\
						.setdefault(gle.against_voucher_type, {})\
						.setdefault(gle.against_voucher, [])\
						.append(gle)

		return self.gl_entries_map.get(party, {})\
			.get(against_voucher_type, {})\
			.get(against_voucher, [])

	def get_payment_term_detail(self, voucher_nos):
		payment_term_map = frappe._dict()
		payment_terms_details = frappe.db.sql(""" select si.name,
			party_account_currency, currency, si.conversion_rate,
			ps.due_date, ps.payment_amount, ps.description
			from `tabSales Invoice` si, `tabPayment Schedule` ps
			where si.name = ps.parent and
			si.docstatus = 1 and si.company = '%s' and
			si.name in (%s) order by ps.due_date
		"""	% (frappe.db.escape(self.filters.company), ','.join(['%s'] *len(voucher_nos))),
		(tuple(voucher_nos)), as_dict = 1)

		for d in payment_terms_details:
			if self.filters.get("customer") and d.currency == d.party_account_currency:
				payment_term_amount = d.payment_amount
			else:
				payment_term_amount = flt(flt(d.payment_amount) * flt(d.conversion_rate), self.currency_precision)

			payment_term_map.setdefault(d.name, []).append(frappe._dict({
				"due_date": d.due_date,
				"payment_term_amount": payment_term_amount,
				"description": d.description
			}))
		return payment_term_map

	def get_chart_data(self, columns, data):
		ageing_columns = columns[self.ageing_col_idx_start : self.ageing_col_idx_start+4]
		rows = []
		for d in data:
			rows.append(
				{
					'values': [d["range{}".format(i+1)] for i in range(5)]
				}
			)

		return {
			"data": {
				'labels': [d.get("label") for d in ageing_columns],
				'datasets': rows
			},
			"type": 'percentage'
		}

def execute(filters=None):
	args = {
		"party_type": "Customer",
		"naming_by": ["Selling Settings", "cust_master_name"],
	}
	return ReceivablePayableReport(filters).run(args)

def get_ageing_data(first_range, second_range, third_range, fourth_range, age_as_on, entry_date, outstanding_amount):
	# [0-30, 30-60, 60-90, 90-120, 120-above]
	outstanding_range = [0.0, 0.0, 0.0, 0.0, 0.0]

	if not (age_as_on and entry_date):
		return [0] + outstanding_range

	age = (getdate(age_as_on) - getdate(entry_date)).days or 0
	index = None
	for i, days in enumerate([first_range, second_range, third_range, fourth_range]):
		if age <= days:
			index = i
			break

	if index is None: index = 4
	outstanding_range[index] = outstanding_amount

	return [age] + outstanding_range

def get_pdc_details(party_type, report_date):
	pdc_details = frappe._dict()
	pdc_via_pe = frappe.db.sql("""
		select
			pref.reference_name as invoice_no, pent.party, pent.party_type,
			pent.posting_date as pdc_date, ifnull(pref.allocated_amount,0) as pdc_amount,
			pent.reference_no as pdc_ref
		from
			`tabPayment Entry` as pent inner join `tabPayment Entry Reference` as pref
		on
			(pref.parent = pent.name)
		where
			pent.docstatus < 2 and pent.posting_date > %s
			and pent.party_type = %s
		""", (report_date, party_type), as_dict=1)

	for pdc in pdc_via_pe:
			pdc_details.setdefault((pdc.invoice_no, pdc.party), []).append(pdc)

	if scrub(party_type):
		amount_field = ("jea.debit_in_account_currency"
			if party_type == 'Supplier' else "jea.credit_in_account_currency")
	else:
		amount_field = "jea.debit + jea.credit"

	pdc_via_je = frappe.db.sql("""
		select
			jea.reference_name as invoice_no, jea.party, jea.party_type,
			je.posting_date as pdc_date, ifnull({0},0) as pdc_amount,
			jea.cheque_no as pdc_ref
		from
			`tabJournal Entry` as je inner join `tabJournal Entry Account` as jea
		on
			(jea.parent = je.name)
		where
			je.docstatus < 2 and je.posting_date > %s
			and jea.party_type = %s
		""".format(amount_field), (report_date, party_type), as_dict=1)

	for pdc in pdc_via_je:
		pdc_details.setdefault((pdc.invoice_no, pdc.party), []).append(pdc)

	return pdc_details

def get_dn_details(party_type, voucher_nos):
	dn_details = frappe._dict()

	if party_type == "Customer":
		for si in frappe.db.sql("""
			select
				parent, GROUP_CONCAT(delivery_note SEPARATOR ', ') as dn
			from
				`tabSales Invoice Item`
			where
				docstatus=1 and delivery_note is not null and delivery_note != ''
				and parent in (%s) group by parent
			""" %(','.join(['%s'] * len(voucher_nos))), tuple(voucher_nos) , as_dict=1):
			dn_details.setdefault(si.parent, si.dn)

		for si in frappe.db.sql("""
			select
				against_sales_invoice as parent, GROUP_CONCAT(parent SEPARATOR ', ') as dn
			from
				`tabDelivery Note Item`
			where
				docstatus=1 and against_sales_invoice is not null and against_sales_invoice != ''
				and against_sales_invoice in (%s)
				group by against_sales_invoice
			""" %(','.join(['%s'] * len(voucher_nos))), tuple(voucher_nos) , as_dict=1):
			if si.parent in dn_details:
				dn_details[si.parent] += ', %s' %(si.dn)
			else:
				dn_details.setdefault(si.parent, si.dn)

	return dn_details

def get_voucher_details(party_type, voucher_nos, dn_details):
	voucher_details = frappe._dict()

	if party_type == "Customer":
		for si in frappe.db.sql("""
			select inv.name, inv.due_date, inv.po_no, GROUP_CONCAT(steam.sales_person SEPARATOR ', ') as sales_person
			from `tabSales Invoice` inv
			left join `tabSales Team` steam on steam.parent = inv.name and steam.parenttype = 'Sales Invoice'
			where inv.docstatus=1 and inv.name in (%s)
			group by inv.name
			""" %(','.join(['%s'] *len(voucher_nos))), (tuple(voucher_nos)), as_dict=1):
				si['delivery_note'] = dn_details.get(si.name)
				voucher_details.setdefault(si.name, si)

	if party_type == "Supplier":
		for pi in frappe.db.sql("""select name, due_date, bill_no, bill_date
			from `tabPurchase Invoice` where docstatus = 1 and name in (%s)
			""" %(','.join(['%s'] *len(voucher_nos))), (tuple(voucher_nos)), as_dict=1):
			voucher_details.setdefault(pi.name, pi)

	for pi in frappe.db.sql("""select name, due_date, bill_no, bill_date from
		`tabJournal Entry` where docstatus = 1 and bill_no is not NULL and name in (%s)
		""" %(','.join(['%s'] *len(voucher_nos))), (tuple(voucher_nos)), as_dict=1):
			voucher_details.setdefault(pi.name, pi)

	return voucher_details
