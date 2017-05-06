# Copyright (c) 2015, Frappe Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, scrub
from frappe.utils import getdate, nowdate, flt, cint

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
		chart = self.get_chart_data(columns, data)
		return columns, data, None, chart

	def get_columns(self, party_naming_by, args):
		columns = [_("Posting Date") + ":Date:80", _(args.get("party_type")) + ":Link/" + args.get("party_type") + ":200"]

		if party_naming_by == "Naming Series":
			columns += [args.get("party_type") + " Name::110"]

		columns += [_("Voucher Type") + "::110", _("Voucher No") + ":Dynamic Link/"+_("Voucher Type")+":120",
			_("Due Date") + ":Date:80"]

		if args.get("party_type") == "Supplier":
			columns += [_("Bill No") + "::80", _("Bill Date") + ":Date:80"]

		for label in ("Invoiced Amount", "Paid Amount", "Outstanding Amount"):
			columns.append({
				"label": label,
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120
			})

		columns += [_("Age (Days)") + ":Int:80"]
		
		self.ageing_col_idx_start = len(columns)

		if not "range1" in self.filters:
			self.filters["range1"] = "30"
		if not "range2" in self.filters:
			self.filters["range2"] = "60"
		if not "range3" in self.filters:
			self.filters["range3"] = "90"
			
		for label in ("0-{range1}".format(range1=self.filters["range1"]),
			"{range1}-{range2}".format(range1=cint(self.filters["range1"])+ 1, range2=self.filters["range2"]),
			"{range2}-{range3}".format(range2=cint(self.filters["range2"])+ 1, range3=self.filters["range3"]),
			"{range3}-{above}".format(range3=cint(self.filters["range3"])+ 1, above=_("Above"))):
				columns.append({
					"label": label,
					"fieldtype": "Currency",
					"options": "currency",
					"width": 120
				})

		columns.append({
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"width": 100
		})
		if args.get("party_type") == "Customer":
			columns += [
				_("Territory") + ":Link/Territory:80", 
				_("Customer Group") + ":Link/Customer Group:120"
			]
		if args.get("party_type") == "Supplier":
			columns += [_("Supplier Type") + ":Link/Supplier Type:80"]
			
		columns.append(_("Remarks") + "::200")
		
		return columns

	def get_data(self, party_naming_by, args):
		from erpnext.accounts.utils import get_currency_precision
		currency_precision = get_currency_precision() or 2
		dr_or_cr = "debit" if args.get("party_type") == "Customer" else "credit"

		voucher_details = self.get_voucher_details(args.get("party_type"))

		future_vouchers = self.get_entries_after(self.filters.report_date, args.get("party_type"))

		if not self.filters.get("company"):
			self.filters["company"] = frappe.db.get_single_value('Global Defaults', 'default_company')

		company_currency = frappe.db.get_value("Company", self.filters.get("company"), "default_currency")

		data = []
		for gle in self.get_entries_till(self.filters.report_date, args.get("party_type")):
			if self.is_receivable_or_payable(gle, dr_or_cr, future_vouchers):
				outstanding_amount = flt(self.get_outstanding_amount(gle, 
					self.filters.report_date, dr_or_cr), currency_precision)
					
				if abs(outstanding_amount) > 0.1/10**currency_precision:
					row = [gle.posting_date, gle.party]

					# customer / supplier name
					if party_naming_by == "Naming Series":
						row += [self.get_party_name(gle.party_type, gle.party)]

					# get due date
					due_date = voucher_details.get(gle.voucher_no, {}).get("due_date", "")

					row += [gle.voucher_type, gle.voucher_no, due_date]

					# get supplier bill details
					if args.get("party_type") == "Supplier":
						row += [
							voucher_details.get(gle.voucher_no, {}).get("bill_no", ""),
							voucher_details.get(gle.voucher_no, {}).get("bill_date", "")
						]

					# invoiced and paid amounts
					invoiced_amount = gle.get(dr_or_cr) if (gle.get(dr_or_cr) > 0) else 0
					paid_amt = invoiced_amount - outstanding_amount
					row += [invoiced_amount, paid_amt, outstanding_amount]

					# ageing data
					entry_date = due_date if self.filters.ageing_based_on == "Due Date" else gle.posting_date
					row += get_ageing_data(cint(self.filters.range1), cint(self.filters.range2),
						cint(self.filters.range3), self.age_as_on, entry_date, outstanding_amount)

					# issue 6371-Ageing buckets should not have amounts if due date is not reached
					if self.filters.ageing_based_on == "Due Date" and getdate(due_date) > getdate(self.filters.report_date):
						row[-1]=row[-2]=row[-3]=row[-4]=0

					if self.filters.get(scrub(args.get("party_type"))):
						row.append(gle.account_currency)
					else:
						row.append(company_currency)

					# customer territory / supplier type
					if args.get("party_type") == "Customer":
						row += [self.get_territory(gle.party), self.get_customer_group(gle.party)]
					if args.get("party_type") == "Supplier":
						row += [self.get_supplier_type(gle.party)]

					row.append(gle.remarks)
					data.append(row)

		return data

	def get_entries_after(self, report_date, party_type):
		# returns a distinct list
		return list(set([(e.voucher_type, e.voucher_no) for e in self.get_gl_entries(party_type)
			if getdate(e.posting_date) > report_date]))

	def get_entries_till(self, report_date, party_type):
		# returns a generator
		return (e for e in self.get_gl_entries(party_type)
			if getdate(e.posting_date) <= report_date)

	def is_receivable_or_payable(self, gle, dr_or_cr, future_vouchers):
		return (
			# advance
			(not gle.against_voucher) or

			# against sales order/purchase order
			(gle.against_voucher_type in ["Sales Order", "Purchase Order"]) or

			# sales invoice/purchase invoice
			(gle.against_voucher==gle.voucher_no and gle.get(dr_or_cr) > 0) or

			# entries adjusted with future vouchers
			((gle.against_voucher_type, gle.against_voucher) in future_vouchers)
		)

	def get_outstanding_amount(self, gle, report_date, dr_or_cr):
		payment_amount = 0.0
		for e in self.get_gl_entries_for(gle.party, gle.party_type, gle.voucher_type, gle.voucher_no):
			if getdate(e.posting_date) <= report_date and e.name!=gle.name:
				payment_amount += (flt(e.credit if gle.party_type == "Customer" else e.debit) - flt(e.get(dr_or_cr)))

		return flt(gle.get(dr_or_cr)) - flt(gle.credit if gle.party_type == "Customer" else gle.debit) - payment_amount

	def get_party_name(self, party_type, party_name):
		return self.get_party_map(party_type).get(party_name, {}).get("customer_name" if party_type == "Customer" else "supplier_name") or ""

	def get_territory(self, party_name):
		return self.get_party_map("Customer").get(party_name, {}).get("territory") or ""
		
	def get_customer_group(self, party_name):
		return self.get_party_map("Customer").get(party_name, {}).get("customer_group") or ""

	def get_supplier_type(self, party_name):
		return self.get_party_map("Supplier").get(party_name, {}).get("supplier_type") or ""

	def get_party_map(self, party_type):
		if not hasattr(self, "party_map"):
			if party_type == "Customer":
				select_fields = "name, customer_name, territory, customer_group"
			elif party_type == "Supplier":
				select_fields = "name, supplier_name, supplier_type"
			
			self.party_map = dict(((r.name, r) for r in frappe.db.sql("select {0} from `tab{1}`"
				.format(select_fields, party_type), as_dict=True)))

		return self.party_map

	def get_voucher_details(self, party_type):
		voucher_details = frappe._dict()

		if party_type == "Customer":
			for si in frappe.db.sql("""select name, due_date
				from `tabSales Invoice` where docstatus=1""", as_dict=1):
					voucher_details.setdefault(si.name, si)

		if party_type == "Supplier":
			for pi in frappe.db.sql("""select name, due_date, bill_no, bill_date
				from `tabPurchase Invoice` where docstatus=1""", as_dict=1):
					voucher_details.setdefault(pi.name, pi)

		return voucher_details

	def get_gl_entries(self, party_type):
		if not hasattr(self, "gl_entries"):
			conditions, values = self.prepare_conditions(party_type)

			if self.filters.get(scrub(party_type)):
				select_fields = "sum(debit_in_account_currency) as debit, sum(credit_in_account_currency) as credit"
			else:
				select_fields = "sum(debit) as debit, sum(credit) as credit"

			self.gl_entries = frappe.db.sql("""select name, posting_date, account, party_type, party, 
				voucher_type, voucher_no, against_voucher_type, against_voucher, 
				account_currency, remarks, {0}
				from `tabGL Entry`
				where docstatus < 2 and party_type=%s and (party is not null and party != '') {1}
				group by voucher_type, voucher_no, against_voucher_type, against_voucher, party
				order by posting_date, party"""
				.format(select_fields, conditions), values, as_dict=True)

		return self.gl_entries

	def prepare_conditions(self, party_type):
		conditions = [""]
		values = [party_type]

		party_type_field = scrub(party_type)

		if self.filters.company:
			conditions.append("company=%s")
			values.append(self.filters.company)

		if self.filters.get(party_type_field):
			conditions.append("party=%s")
			values.append(self.filters.get(party_type_field))

		if party_type_field=="customer":
			if self.filters.get("customer_group"):
				lft, rgt = frappe.db.get_value("Customer Group", 
					self.filters.get("customer_group"), ["lft", "rgt"])
			
				conditions.append("""party in (select name from tabCustomer 
					where exists(select name from `tabCustomer Group` where lft >= {0} and rgt <= {1} 
						and name=tabCustomer.customer_group))""".format(lft, rgt))
						
			if self.filters.get("credit_days_based_on"):
				conditions.append("party in (select name from tabCustomer where credit_days_based_on=%s)")
				values.append(self.filters.get("credit_days_based_on"))

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
			
	def get_chart_data(self, columns, data):
		ageing_columns = columns[self.ageing_col_idx_start : self.ageing_col_idx_start+4]
		
		rows = []
		for d in data:
			rows.append(d[self.ageing_col_idx_start : self.ageing_col_idx_start+4])

		if rows:
			rows.insert(0, [[d.get("label")] for d in ageing_columns])
		
		return {
			"data": {
				'rows': rows
			},
			"chart_type": 'pie'
		}

def execute(filters=None):
	args = {
		"party_type": "Customer",
		"naming_by": ["Selling Settings", "cust_master_name"],
	}
	return ReceivablePayableReport(filters).run(args)

def get_ageing_data(first_range, second_range, third_range, age_as_on, entry_date, outstanding_amount):
	# [0-30, 30-60, 60-90, 90-above]
	outstanding_range = [0.0, 0.0, 0.0, 0.0]

	if not (age_as_on and entry_date):
		return [0] + outstanding_range

	age = (getdate(age_as_on) - getdate(entry_date)).days or 0
	index = None
	for i, days in enumerate([first_range, second_range, third_range]):
		if age <= days:
			index = i
			break

	if index is None: index = 3
	outstanding_range[index] = outstanding_amount

	return [age] + outstanding_range
