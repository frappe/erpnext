# Copyright (c) 2015, Frappe Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe import _, scrub
from frappe.utils import getdate, nowdate, flt, cint, formatdate, cstr
from frappe.desk.query_report import group_report_data, hide_columns_if_filtered
from erpnext.accounts.utils import get_allow_cost_center_in_entry_of_bs_account, get_allow_project_in_entry_of_bs_account
from erpnext.accounts.report.financial_statements import get_cost_centers_with_children

class ReceivablePayableReport(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.filters.report_date = getdate(self.filters.report_date or nowdate())
		self.age_as_on = getdate(nowdate()) \
			if self.filters.report_date > getdate(nowdate()) \
			else self.filters.report_date

	def run(self, args):
		self.filters.party_type = args.get('party_type')
		self.party_naming_by = frappe.db.get_value(args.get("naming_by")[0], None, args.get("naming_by")[1])

		self.validate_filters()

		columns = self.get_columns()
		data = self.get_data()
		data_out = self.get_grouped_data(columns, data)
		chart = self.get_chart_data(columns, data)

		return columns, data_out, None, chart

	def validate_ageing_filter(self):
		self.ageing_range = [cint(r.strip()) for r in self.filters.get('ageing_range', "").split(",") if r]
		self.ageing_range = sorted(list(set(self.ageing_range)))
		self.ageing_column_count = len(self.ageing_range) + 1

	def validate_filters(self):
		self.validate_ageing_filter()

		if self.filters.get('cost_center'):
			self.filters.cost_center = get_cost_centers_with_children(self.filters.get("cost_center"))

		if self.filters.get("project"):
			if not isinstance(self.filters.get("project"), list):
				self.filters.project = [d.strip() for d in cstr(self.filters.project).strip().split(',') if d]

		if self.filters.get("sales_person"):
			sales_person = self.filters.sales_person
			self.filters.sales_person = frappe.get_all("Sales Person",
				filters={'name': ['descendants of', self.filters.sales_person]})
			self.filters.sales_person = set([sales_person] + [d.name for d in self.filters.sales_person])

	def get_columns(self):
		party_column_width = 80 if self.party_naming_by == "Naming Series" else 200

		columns = [
			{
				"label": _("Date"),
				"fieldtype": "Date",
				"fieldname": "posting_date",
				"width": 80
			},
			{
				"label": _(self.filters.get("party_type")),
				"fieldtype": "Link",
				"fieldname": "party",
				"filter_fieldname": scrub(self.filters.get("party_type")),
				"options": self.filters.get("party_type"),
				"width": party_column_width if self.filters.get("group_by", "Ungrouped") == "Ungrouped" else 300
			}
		]

		if self.filters.get("group_by", "Ungrouped") != "Ungrouped":
			columns = list(reversed(columns))

		if self.party_naming_by == "Naming Series":
			columns.append({
				"label": _(self.filters.get("party_type") + " Name"),
				"fieldtype": "Data",
				"fieldname": "party_name",
				"width": 180
			})

		columns += [
			{
				"label": _("Voucher Type"),
				"fieldtype": "Data",
				"fieldname": "voucher_type",
				"width": 120
			},
			{
				"label": _("Voucher No"),
				"fieldtype": "Dynamic Link",
				"fieldname": "voucher_no",
				"width": 150,
				"options": "voucher_type",
			}
		]

		if self.filters.get("party_type") != "Employee":
			columns.append({
				"label": _("Due Date"),
				"fieldtype": "Date",
				"fieldname": "due_date",
				"width": 80,
			})

		if self.filters.get("party_type") == "Supplier":
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

		invoiced_label = "Invoiced Amount"
		paid_label = "Paid Amount"
		return_label = "Returned Amount"
		if self.filters.get("party_type") == "Customer":
			return_label = "Credit Note"
		elif self.filters.get("party_type") == "Supplier":
			return_label = "Debit Note"
		elif self.filters.get("party_type") == "Employee":
			invoiced_label = "Paid Amount"
			paid_label = "Claimed Amount"

		columns += [
			{
				"label": _(invoiced_label),
				"fieldname": "invoiced_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120
			},
			{
				"label": _(paid_label),
				"fieldname": "paid_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120
			},
			{
				"label": _(return_label),
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
			"label": _("Age"),
			"fieldtype": "Int",
			"fieldname": "age",
			"width": 50,
		})

		if self.filters.get("party_type") == "Employee":
			columns.append({
				"label": _("Account"),
				"fieldtype": "Link",
				"fieldname": "account",
				"options": "Account",
				"width": 150
			})

		if get_allow_cost_center_in_entry_of_bs_account():
			columns.append({
				"label": _("Cost Center"),
				"fieldtype": "Link",
				"fieldname": "cost_center",
				"options": "Cost Center",
				"width": 100,
				"hide_if_filtered": 1
			})

		if get_allow_project_in_entry_of_bs_account():
			columns.append({
				"label": _("Project"),
				"fieldtype": "Link",
				"fieldname": "project",
				"options": "Project",
				"width": 100,
				"hide_if_filtered": 1
			})

		columns.append({
			"fieldname": "remarks",
			"label": _("Remarks"),
			"fieldtype": "Data",
			"width": 200
		})

		self.ageing_columns = self.get_ageing_columns()
		columns += self.ageing_columns

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

		if self.filters.get('party_type') == 'Customer':
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
					"label": _("Sales Person"),
					"fieldtype": "Data",
					"fieldname": "sales_person",
					"width": 150,
				},
				{
					"fieldname": "territory",
					"label": _("Territory"),
					"fieldtype": "Link",
					"options": "Territory",
					"width": 100
				},
				{
					"fieldname": "customer_group",
					"label": _("Customer Group"),
					"fieldtype": "Link",
					"options": "Customer Group",
					"width": 100
				},
				{
					"label": _("Customer Contact"),
					"fieldtype": "Link",
					"fieldname": "contact",
					"options": "Contact",
					"width": 100
				}
			]
		if self.filters.get("party_type") == "Supplier":
			columns += [
				{
					"fieldname": "supplier_group",
					"label": _("Supplier Group"),
					"fieldtype": "Link",
					"options": "Supplier Group",
					"width": 120
				}
			]

		return columns

	def get_ageing_columns(self):
		ageing_columns = []
		lower_limit = 0
		for i, upper_limit in enumerate(self.ageing_range):
			ageing_columns.append({
				"label": "{0}-{1}".format(lower_limit, upper_limit),
				"fieldname": "range{}".format(i+1),
				"fieldtype": "Currency",
				"options": "currency",
				"ageing_column": 1,
				"width": 120
			})
			lower_limit = upper_limit + 1

		ageing_columns.append({
			"label": "{0}-Above".format(lower_limit),
			"fieldname": "range{}".format(self.ageing_column_count),
			"fieldtype": "Currency",
			"options": "currency",
			"ageing_column": 1,
			"width": 120
		})
		return ageing_columns

	def get_data(self):
		from erpnext.accounts.utils import get_currency_precision
		self.currency_precision = get_currency_precision() or 2

		self.dr_or_cr = "debit" if erpnext.get_party_account_type(self.filters.get("party_type")) == "Receivable" else "credit"
		if self.filters.get("party_type") == "Employee":
			self.dr_or_cr = "debit"

		self.reverse_dr_or_cr = "credit" if self.dr_or_cr == "debit" else "debit"

		future_vouchers = self.get_entries_after(self.filters.report_date, self.filters.get("party_type"))

		if not self.filters.get("company"):
			self.filters["company"] = frappe.db.get_single_value('Global Defaults', 'default_company')

		self.company_currency = frappe.get_cached_value('Company',  self.filters.get("company"), "default_currency")

		return_entries = self.get_return_entries(self.filters.get("party_type"))
		employee_advances_already_added = []

		data = []
		self.pdc_details = get_pdc_details(self.filters.get("party_type"), self.filters.report_date)
		gl_entries_data = self.get_entries_till(self.filters.report_date, self.filters.get("party_type"))

		voucher_nos = [d.voucher_no for d in gl_entries_data] or []

		if gl_entries_data:
			dn_details = get_dn_details(self.filters.get("party_type"), voucher_nos)
			self.voucher_details = get_voucher_details(self.filters.get("party_type"), voucher_nos, dn_details)

		self.sales_person_details = get_sales_person_details(self.filters.get("party_type"), voucher_nos)

		if self.filters.party_type == "Employee":
			employee_advances = list(set([d.against_voucher for d in gl_entries_data or [] if d.against_voucher_type == "Employee Advance"]))
			self.employee_advance_details = get_employee_advance_details(employee_advances)

		if self.filters.based_on_payment_terms and gl_entries_data:
			self.payment_term_map = self.get_payment_term_detail(voucher_nos)

		for gle in gl_entries_data:
			if self.is_receivable_or_payable(gle, future_vouchers, return_entries)\
					and self.is_in_cost_center(gle) and self.is_in_project(gle) and self.is_in_sales_person(gle)\
					and self.is_in_item_filtered_invoice(gle):
				outstanding_amount, credit_note_amount, payment_amount = self.get_outstanding_amount(
					gle, self.filters.report_date, self.dr_or_cr, return_entries)

				temp_outstanding_amt = outstanding_amount
				temp_credit_note_amt = credit_note_amount

				if abs(outstanding_amount) >= 0.1/10**self.currency_precision:
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
								row = self.prepare_row(gle, term_outstanding_amount,
									d.credit_note_amount, d.due_date, d.payment_amount , d.payment_term_amount,
									d.description, d.pdc_amount, d.pdc_details)
								data.append(row)

						if credit_note_amount:
							row = self.prepare_row_without_payment_terms(gle, temp_outstanding_amt, temp_credit_note_amt)
							data.append(row)

					else:
						row = self.prepare_row_without_payment_terms(gle, outstanding_amount, credit_note_amount)
						data.append(row)

			elif self.filters.party_type == "Employee" and gle.against_voucher_type == "Employee Advance":
				ea_details = self.employee_advance_details.get(gle.against_voucher, frappe._dict())
				if gle.against_voucher not in employee_advances_already_added and self.is_in_cost_center(ea_details) and self.is_in_project(ea_details):
					employee_advances_already_added.append(gle.against_voucher)
					outstanding_amount, return_amount, payment_amount = self.get_employee_advance_outstanding(gle,
						self.filters.report_date)

					if abs(outstanding_amount) > 0.1 / 10 ** self.currency_precision:
						ea = gle.copy()

						ea.credit = 0
						ea.debit = payment_amount
						ea.voucher_type = gle.against_voucher_type
						ea.voucher_no = gle.against_voucher
						ea.remarks = ea_details.purpose
						ea.cost_center = ea_details.cost_center
						ea.project = ea_details.project
						row = self.prepare_row_without_payment_terms(ea, outstanding_amount, return_amount)
						data.append(row)

		return data

	def get_grouped_data(self, columns, data):
		level1 = self.filters.get("group_by", "").replace("Group by ", "")
		level2 = self.filters.get("group_by_2", "").replace("Group by ", "")
		level1_fieldname = "party" if level1 in ['Customer', 'Supplier', 'Employee'] else scrub(level1)
		level2_fieldname = "party" if level2 in ['Customer', 'Supplier', 'Employee'] else scrub(level2)

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
			if not group_object.group_field:
				group_object.totals['party'] = "'Total'"
			elif group_object.group_field == 'party':
				group_object.totals['party'] = group_object.group_value
				group_object.totals['party_name'] = group_object.rows[0].get('party_name')
			else:
				group_object.totals['party'] = "'{0}: {1}'".format(group_object.group_label, group_object.group_value)

			if group_object.group_field == 'party':
				group_object.totals['currency'] = group_object.rows[0].get("currency")

				if self.get_party_map(self.filters.party_type):
					group_object.tax_id = self.party_map.get(group_object.group_value, {}).get("tax_id")
					group_object.payment_terms = self.party_map.get(group_object.group_value, {}).get("payment_terms")
					group_object.credit_limit = self.party_map.get(group_object.group_value, {}).get("credit_limit")

			group_object.rows = self.group_aggregate_age(group_object.rows, columns, grouped_by)
			if group_object.rows is None:
				group_object.totals = None

		return group_report_data(data, group_by, total_fields=total_fields, postprocess_group=postprocess_group,
			group_by_labels=group_by_labels)

	def group_aggregate_age(self, data, columns, grouped_by=None):
		if not self.filters.from_date and not self.filters.to_date:
			return data

		within_limit = []
		below_limit = []
		above_limit = []

		if self.filters.ageing_based_on == "Due Date":
			date_field = "due_date"
		elif self.filters.ageing_based_on == "Supplier Invoice Date":
			date_field = "bill_date"
		else:
			date_field = "posting_date"

		for d in data:
			if d._isGroupTotal or d._isGroup:
				within_limit.append(d)
			elif self.filters.from_date and d[date_field] < getdate(self.filters.from_date):
				below_limit.append(d)
			elif self.filters.to_date and d[date_field] > getdate(self.filters.to_date):
				above_limit.append(d)
			else:
				within_limit.append(d)

		if not within_limit:
			return None

		if not below_limit and not above_limit:
			return data

		total_fields = [c['fieldname'] for c in columns
			if c['fieldtype'] in ['Float', 'Currency', 'Int'] and c['fieldname'] != 'age']

		below_limit_total = group_report_data(below_limit, None, total_fields=total_fields, totals_only=True)
		below_limit_total = below_limit_total[0] if below_limit_total else {}
		above_limit_total = group_report_data(above_limit, None, total_fields=total_fields, totals_only=True)
		above_limit_total = above_limit_total[0] if above_limit_total else {}
		within_limit_total = group_report_data(within_limit, None, total_fields=total_fields, totals_only=True)
		within_limit_total = within_limit_total[0] if within_limit_total else {}

		if grouped_by:
			below_limit_total.update(grouped_by)
			within_limit_total.update(grouped_by)
			above_limit_total.update(grouped_by)

		below_limit_total['party'] = _("'Before {0} Total'").format(formatdate(self.filters.from_date))
		above_limit_total['party'] = _("'After {0} Total'").format(formatdate(self.filters.to_date))

		within_limit_total['_excludeFromTotal'] = True
		within_limit_total['_bold'] = True
		if self.filters.from_date and self.filters.to_date:
			within_limit_total['party'] = _("'Total Between {0} and {1}'").format(formatdate(self.filters.from_date), formatdate(self.filters.to_date))
		elif self.filters.from_date:
			within_limit_total['party'] = _("'Total of {0} and Above'").format(formatdate(self.filters.from_date))
		elif self.filters.to_date:
			within_limit_total['party'] = _("'Total of {0} and Below'").format(formatdate(self.filters.to_date))

		out = []
		if self.filters.to_date:
			out.append(above_limit_total)

		if within_limit:
			if self.filters.to_date:
				out.append({})

			out += within_limit
			out.append(within_limit_total)

			if self.filters.from_date:
				out.append({})

		if self.filters.from_date:
			out.append(below_limit_total)

		return out

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

	def prepare_row_without_payment_terms(self, gle, outstanding_amount, credit_note_amount):
		pdc_list = self.pdc_details.get((gle.voucher_no, gle.party), [])
		pdc_amount = 0
		pdc_details = []
		for d in pdc_list:
			pdc_amount += flt(d.pdc_amount)
			if pdc_amount and d.pdc_ref and d.pdc_date:
				pdc_details.append(cstr(d.pdc_ref) + "/" + formatdate(d.pdc_date))

		row = self.prepare_row(gle, outstanding_amount, credit_note_amount, pdc_amount=pdc_amount, pdc_details=pdc_details)

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

	def prepare_row(self, gle, outstanding_amount, credit_note_amount,
		due_date=None, paid_amt=None, payment_term_amount=None, payment_term=None, pdc_amount=None, pdc_details=None):
		row = frappe._dict({"posting_date": gle.posting_date, "party": gle.party})

		# customer / supplier name
		if self.party_naming_by == "Naming Series":
			row["party_name"] = self.get_party_name(gle.party_type, gle.party)

		if self.filters.get("party_type") == 'Customer':
			row["contact"] = self.get_customer_contact(gle.party_type, gle.party)

		# get due date
		if not due_date:
			due_date = self.voucher_details.get(gle.voucher_no, {}).get("due_date", "")
		bill_date = self.voucher_details.get(gle.voucher_no, {}).get("bill_date", "")

		row["voucher_type"] = gle.voucher_type
		row["voucher_no"] = gle.voucher_no
		row["due_date"] = due_date

		row["account"] = gle.account
		row["cost_center"] = gle.cost_center
		row["project"] = gle.project

		# get supplier bill details
		if self.filters.get("party_type") == "Supplier":
			row["bill_no"] = self.voucher_details.get(gle.voucher_no, {}).get("bill_no", "")
			row["bill_date"] = bill_date

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

		row["age"], ageing_data = get_ageing_data(self.ageing_range, self.age_as_on, entry_date, outstanding_amount)
		for i, age_range_value in enumerate(ageing_data):
			row["range{0}".format(i+1)] = age_range_value

		# issue 6371-Ageing buckets should not have amounts if due date is not reached
		if self.filters.ageing_based_on == "Due Date" \
				and getdate(due_date) > getdate(self.filters.report_date):
			for i in range(self.ageing_column_count):
				row["range{}".format(i+1)] = 0

		if self.filters.ageing_based_on == "Supplier Invoice Date" \
				and getdate(bill_date) > getdate(self.filters.report_date):
			for i in range(self.ageing_column_count):
				row["range{}".format(i+1)] = 0

		if self.filters.get(scrub(self.filters.get("party_type"))) or self.filters.get("account"):
			row["currency"] = gle.account_currency
		else:
			row["currency"] = self.company_currency

		self.account_currency = row["currency"]

		remaining_balance = outstanding_amount - flt(pdc_amount)
		pdc_details = ", ".join(pdc_details)

		row["pdc/lc_ref"] = pdc_details
		row["pdc/lc_amount"] = pdc_amount
		row["remaining_balance"] = remaining_balance

		if self.filters.get('party_type') == 'Customer':
			# customer LPO
			row["po_no"] = self.voucher_details.get(gle.voucher_no, {}).get("po_no")

			# Delivery Note
			row["delivery_note"] = self.voucher_details.get(gle.voucher_no, {}).get("delivery_note")

		# customer territory / supplier group
		if self.filters.get("party_type") == "Customer":
			row["territory"] = self.get_territory(gle.party)
			row["customer_group"] = self.get_customer_group(gle.party)
			row["sales_person"] = ", ".join(self.get_sales_persons(gle.voucher_no, gle.against_voucher))
		if self.filters.get("party_type") == "Supplier":
			row["supplier_group"] = self.get_supplier_group(gle.party)

		row["remarks"] = gle.remarks

		return row

	def get_entries_after(self, report_date, party_type):
		# returns a distinct list
		return list(set([(e.voucher_type, e.voucher_no) for e in self.get_gl_entries(party_type, report_date, for_future=True)]))

	def get_entries_till(self, report_date, party_type):
		# returns a generator
		return self.get_gl_entries(party_type, report_date)

	def is_receivable_or_payable(self, gle, future_vouchers, return_entries):
		return (
			# advance
			(not gle.against_voucher) or

			# against sales order/purchase order
			(gle.against_voucher_type in ["Sales Order", "Purchase Order"]) or

			# sales invoice/purchase invoice
			(gle.against_voucher==gle.voucher_no and gle.get(self.dr_or_cr) - gle.get(self.reverse_dr_or_cr) > 0) or

			# standalone credit notes
			(gle.against_voucher==gle.voucher_no and gle.voucher_no in return_entries and not return_entries.get(gle.voucher_no)) or

			# entries adjusted with future vouchers
			((gle.against_voucher_type, gle.against_voucher) in future_vouchers)
		)

	def is_in_cost_center(self, gle):
		if self.filters.get("cost_center"):
			return gle.cost_center and gle.cost_center in self.filters.cost_center
		else:
			return True

	def is_in_project(self, gle):
		if self.filters.get("project"):
			return gle.project and gle.project in self.filters.project
		else:
			return True

	def is_in_sales_person(self, gle):
		if self.filters.get("sales_person"):
			sales_persons = self.get_sales_persons(gle.voucher_no, gle.against_voucher)
			return bool([sp for sp in sales_persons if sp in self.filters.sales_person])
		else:
			return True

	def is_in_item_filtered_invoice(self, gle):
		if self.filters.get("has_item"):
			return gle.voucher_type == self.get_invoice_doctype() and gle.voucher_no in self.get_item_filtered_invoices()
		else:
			return True

	def get_item_filtered_invoices(self):
		if not self.filters.get('has_item') or self.filters.get("party_type") not in ['Customer', 'Supplier']:
			return []

		if not hasattr(self, 'item_filtered_invoices'):
			item_doctype = self.get_invoice_doctype()
			self.item_filtered_invoices = set(frappe.db.sql_list("""
				select distinct parent from `tab{dt} Item` where item_code = %s
			""".format(dt=item_doctype), self.filters.get('has_item')))

		return self.item_filtered_invoices

	def get_invoice_doctype(self):
		if self.filters.get("party_type") in ['Customer', 'Supplier']:
			return "Sales Invoice" if self.filters.get("party_type") == "Customer" else "Purchase Invoice"

	def get_return_entries(self, party_type):
		doctype = None
		if party_type == "Customer":
			doctype = "Sales Invoice"
		elif party_type == "Supplier":
			doctype = "Purchase Invoice"

		if doctype:
			return_entries = frappe._dict(frappe.get_all(doctype,
				filters={"is_return": 1, "docstatus": 1}, fields=["name", "return_against"], as_list=1))
			return return_entries
		else:
			return []

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

	def get_employee_advance_outstanding(self, gle, report_date):
		claimed_amount, payment_amount, return_amount = 0.0, 0.0, 0.0

		for e in self.get_gl_entries_for(gle.party, gle.party_type, gle.against_voucher_type, gle.against_voucher):
			if getdate(e.posting_date) <= report_date:
				payment_amount += flt(e.debit, self.currency_precision)

				if e.voucher_type == "Expense Claim":
					claimed_amount += flt(e.credit, self.currency_precision)
				else:
					return_amount += flt(e.credit, self.currency_precision)

		outstanding_amount = payment_amount - claimed_amount - return_amount
		return outstanding_amount, return_amount, payment_amount

	def get_party_name(self, party_type, party_name):
		return self.get_party_map(party_type).get(party_name, {}).get(frappe.scrub(party_type) + "_name", '')

	def get_customer_contact(self, party_type, party_name):
		return self.get_party_map(party_type).get(party_name, {}).get("customer_primary_contact")

	def get_territory(self, party_name):
		return self.get_party_map("Customer").get(party_name, {}).get("territory")

	def get_sales_persons(self, voucher_no, against_voucher):
		return self.sales_person_details.get(voucher_no, [])\
			or self.sales_person_details.get(against_voucher, [])

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
						p.payment_terms, p.tax_id
					from `tabCustomer` p
					left join `tabSales Team` steam on steam.parent = p.name and steam.parenttype = 'Customer'
					group by p.name
				""", as_dict=True)
			elif party_type == "Supplier":
				party_data = frappe.db.sql("""
					select p.name, p.supplier_name, p.supplier_group, p.tax_id, p.payment_terms
					from `tabSupplier` p
				""", as_dict=True)
			elif party_type == "Employee":
				party_data = frappe.db.sql("""
					select p.name, p.employee_name, p.department, p.designation, p.employment_type
					from `tabEmployee` p
				""", as_dict=True)
			else:
				party_data = []

			self.party_map = dict([(r.name, r) for r in party_data])

		return self.party_map

	def get_gl_entries(self, party_type, date=None, for_future=False):
		conditions, values = self.prepare_conditions(party_type)

		if self.filters.get(scrub(party_type)) or self.filters.get("account"):
			select_fields = "sum(gle.debit_in_account_currency) as debit, sum(gle.credit_in_account_currency) as credit"
		else:
			select_fields = "sum(gle.debit) as debit, sum(gle.credit) as credit"

		if date and not for_future:
			conditions += " and gle.posting_date <= '%s'" % date

		if date and for_future:
			conditions += " and gle.posting_date > '%s'" % date

		self.gl_entries = frappe.db.sql("""
			select
				gle.name, gle.posting_date, gle.account, gle.party_type, gle.party, gle.voucher_type, gle.voucher_no,
				gle.against_voucher_type, gle.against_voucher, gle.account_currency, gle.remarks, gle.cost_center, gle.project,
				{select_fields}
			from
				`tabGL Entry` gle
			where
				gle.docstatus < 2 and gle.party_type=%s and (gle.party is not null and gle.party != '') {conditions}
				group by gle.voucher_type, gle.voucher_no, gle.against_voucher_type, gle.against_voucher, gle.party
				order by gle.posting_date, gle.party""".format(  # nosec
			select_fields=select_fields,
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

		elif party_type_field=="supplier":
			account_type = "Payable"
			if self.filters.get("supplier_group"):
				conditions.append("""gle.party in (select name from tabSupplier
					where supplier_group=%s)""")
				values.append(self.filters.get("supplier_group"))

		elif party_type_field == "employee":
			account_type = ['in', ['Payable', 'Receivable']]
			if self.filters.get("department"):
				lft, rgt = frappe.db.get_value("Department",
					self.filters.get("department"), ["lft", "rgt"])

				conditions.append("""gle.party in (select name from tabEmployee
					where exists(select name from `tabDepartment` where lft >= {0} and rgt <= {1}
						and name=tabEmployee.department))""".format(lft, rgt))

			if self.filters.get("designation"):
				conditions.append("gle.party in (select name from tabEmployee where designation=%s)")
				values.append(self.filters.get("designation"))

			if self.filters.get("branch"):
				conditions.append("gle.party in (select name from tabEmployee where branch=%s)")
				values.append(self.filters.get("branch"))

		if self.filters.get("account"):
			accounts = [self.filters.get("account")]
		else:
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
		rows = []
		for d in data:
			rows.append(
				{
					'values': [d["range{}".format(i+1)] for i in range(self.ageing_column_count)]
				}
			)

		return {
			"data": {
				'labels': [col.get('label') for col in self.ageing_columns],
				'datasets': rows
			},
			"colors": ['light-blue', 'blue', 'purple', 'orange', 'red'],
			"type": 'percentage',
			"fieldtype": "Currency",
			"options": getattr(self, 'account_currency', None)
		}

def execute(filters=None):
	args = {
		"party_type": "Customer",
		"naming_by": ["Selling Settings", "cust_master_name"],
	}
	return ReceivablePayableReport(filters).run(args)

def get_ageing_data(ageing_range, age_as_on, entry_date, outstanding_amount):
	outstanding_range = [0.0] * (len(ageing_range) + 1)

	if not (age_as_on and entry_date):
		return [0] + outstanding_range

	age = (getdate(age_as_on) - getdate(entry_date)).days or 0
	index = None
	for i, days in enumerate(ageing_range):
		if age <= days:
			index = i
			break

	if index is None:
		index = len(ageing_range)

	outstanding_range[index] = outstanding_amount

	return age, outstanding_range

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
			if erpnext.get_party_account_type(party_type) == 'Payable' else "jea.credit_in_account_currency")
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
				parent, GROUP_CONCAT(DISTINCT delivery_note SEPARATOR ', ') as dn
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
			select inv.name, inv.due_date, inv.po_no
			from `tabSales Invoice` inv
			where inv.docstatus=1 and inv.name in (%s)
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


def get_sales_person_details(party_type, voucher_nos):
	sales_persons = {}

	if party_type == "Customer" and voucher_nos:
		data = frappe.db.sql("""
			select parent, sales_person
			from `tabSales Team`
			where parent in %s and docstatus = 1 
		""", [voucher_nos], as_dict=1)

		for d in data:
			sales_persons.setdefault(d.parent, []).append(d.sales_person)

	return sales_persons

def get_employee_advance_details(names):
	details = {}

	if names:
		employee_advances = frappe.db.sql("""
			select ea.name, ea.cost_center, ea.project, ea.purpose
			from `tabEmployee Advance` ea
			where ea.docstatus = 1 and ea.name in ({0})
			""".format(','.join(['%s'] * len(names))), names, as_dict=1)

		for d in employee_advances:
			details[d.name] = d

	return details
