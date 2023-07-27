# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, scrub
from frappe.utils import flt, cint, getdate
from erpnext.accounts.party import get_partywise_advanced_payment_amount
from erpnext.accounts.report.accounts_receivable.accounts_receivable import ReceivablePayableReport
from six import iteritems

def execute(filters=None):
	args = {
		"party_type": "Customer",
		"naming_by": ["Selling Settings", "cust_master_name"],
	}

	return AccountsReceivableSummary(filters).run(args)

class AccountsReceivableSummary(ReceivablePayableReport):
	def run(self, args):
		self.party_type = args.get('party_type')
		self.party_naming_by = frappe.db.get_value(args.get("naming_by")[0], None, args.get("naming_by")[1])
		self.filters.ageing_based_on = "Due Date"

		self.get_columns()
		self.get_data(args)
		return self.columns, self.data

	def get_data(self, args):
		self.data = []

		self.receivables= ReceivablePayableReport(self.filters).run(args)[1]

		self.get_party_total(args)

		for party, party_dict in iteritems(self.party_total):
			if party_dict.over_due < 500:
				continue

			row = frappe._dict()

			row.party = party

			if self.party_naming_by == "Naming Series":
				row.party_name = frappe.get_cached_value(self.party_type, party, scrub(self.party_type) + "_name")

			row.update(party_dict)		

			self.data.append(row)

	def get_party_total(self, args):
		self.party_total = frappe._dict()

		for d in self.receivables:
			self.init_party_total(d)

			# Add all amount columns
			for k in list(self.party_total[d.party]):
				if k not in ["currency", "sales_person","primary_address","due_date"]:
					self.party_total[d.party][k] += d.get(k, 0.0)
			due_date= d.due_date if d.due_date is  not None else getdate()
			d.over_due=d.outstanding  if (getdate() - due_date).days >0 else 0
			self.set_party_details(d)

	def init_party_total(self, row):
		self.party_total.setdefault(row.party, frappe._dict({
			"invoiced": 0.0,
			"paid": 0.0,
			"credit_note": 0.0,
			"outstanding": 0.0,
			"range1": 0.0,
			"range2": 0.0,
			"range3": 0.0,
			"range4": 0.0,
			"range5": 0.0,
			"over_due": 0.0,
			"sales_person": '',
			"primary_address": '',
			"due_date": getdate()
		}))

	def set_party_details(self, row):
		self.party_total[row.party].currency = row.currency

		for key in ('territory', 'customer_group'):
			if row.get(key):
				self.party_total[row.party][key] = row.get(key)

		if row.sales_person:
			self.party_total[row.party].sales_person =row.sales_person

		if row.primary_address:
			self.party_total[row.party].primary_address =row.primary_address

		if row.over_due:
			self.party_total[row.party].over_due +=row.over_due

	def get_columns(self):
		self.columns = []
		self.add_column(label=_(self.party_type), fieldname='party',
			fieldtype='Link', options=self.party_type, width=200)
		self.add_column(label="Address", fieldname='primary_address', 
			fieldtype='Link', options='Address', width=160)

		self.add_column(label=_('Territory'), fieldname='territory', 
			fieldtype='Link', options='Territory',  width=80)

		self.add_column(label=_('Sales Person'), fieldname='sales_person', 
			fieldtype='Data', width=80)
		
		if self.filters.show_aging_columns:
			self.setup_ageing_columns()

		self.add_column(label="Total OverDue", fieldname='over_due')
		self.add_column(_('Balance'), fieldname='outstanding')


	def setup_ageing_columns(self):
		for i, label in enumerate(["0-{range1}".format(range1=self.filters["range1"]),
			"{range1}-{range2}".format(range1=cint(self.filters["range1"])+ 1, range2=self.filters["range2"]),
			"{range2}-{range3}".format(range2=cint(self.filters["range2"])+ 1, range3=self.filters["range3"]),
			"{range3}-{range4}".format(range3=cint(self.filters["range3"])+ 1, range4=self.filters["range4"]),
			"{range4}-{above}".format(range4=cint(self.filters["range4"])+ 1, above=_("Above"))]):
				self.add_column(label=label, fieldname='range' + str(i+1),width=80)


