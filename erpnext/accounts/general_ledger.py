# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe.utils import flt, cstr, cint
from frappe import _
from frappe.model.meta import get_field_precision
from erpnext.accounts.doctype.budget.budget import validate_expense_against_budget


class StockAccountInvalidTransaction(frappe.ValidationError): pass

def make_gl_entries(gl_map, cancel=False, adv_adj=False, merge_entries=True, update_outstanding='Yes', from_repost=False):
	if gl_map:
		if not cancel:
			gl_map = process_gl_map(gl_map, merge_entries)
			if gl_map and len(gl_map) > 1:
				save_entries(gl_map, adv_adj, update_outstanding, from_repost)
			else:
				frappe.throw(_("Incorrect number of General Ledger Entries found. You might have selected a wrong Account in the transaction."))
		else:
			delete_gl_entries(gl_map, adv_adj=adv_adj, update_outstanding=update_outstanding)

def process_gl_map(gl_map, merge_entries=True):
	if merge_entries:
		gl_map = merge_similar_entries(gl_map)
	for entry in gl_map:
		# toggle debit, credit if negative entry
		if flt(entry.debit) < 0:
			entry.credit = flt(entry.credit) - flt(entry.debit)
			entry.debit = 0.0

		if flt(entry.debit_in_account_currency) < 0:
			entry.credit_in_account_currency = \
				flt(entry.credit_in_account_currency) - flt(entry.debit_in_account_currency)
			entry.debit_in_account_currency = 0.0

		if flt(entry.credit) < 0:
			entry.debit = flt(entry.debit) - flt(entry.credit)
			entry.credit = 0.0

		if flt(entry.credit_in_account_currency) < 0:
			entry.debit_in_account_currency = \
				flt(entry.debit_in_account_currency) - flt(entry.credit_in_account_currency)
			entry.credit_in_account_currency = 0.0

	return gl_map

def merge_similar_entries(gl_map):
	merged_gl_map = []
	for entry in gl_map:
		# if there is already an entry in this account then just add it
		# to that entry
		same_head = check_if_in_list(entry, merged_gl_map)
		if same_head:
			same_head.debit	= flt(same_head.debit) + flt(entry.debit)
			same_head.debit_in_account_currency	= \
				flt(same_head.debit_in_account_currency) + flt(entry.debit_in_account_currency)
			same_head.credit = flt(same_head.credit) + flt(entry.credit)
			same_head.credit_in_account_currency = \
				flt(same_head.credit_in_account_currency) + flt(entry.credit_in_account_currency)
		else:
			merged_gl_map.append(entry)

	# filter zero debit and credit entries
	merged_gl_map = filter(lambda x: flt(x.debit, 9)!=0 or flt(x.credit, 9)!=0, merged_gl_map)
	return merged_gl_map

def check_if_in_list(gle, gl_map):
	for e in gl_map:
		if e.account == gle.account \
			and cstr(e.get('party_type'))==cstr(gle.get('party_type')) \
			and cstr(e.get('party'))==cstr(gle.get('party')) \
			and cstr(e.get('against_voucher'))==cstr(gle.get('against_voucher')) \
			and cstr(e.get('against_voucher_type')) == cstr(gle.get('against_voucher_type')) \
			and cstr(e.get('cost_center')) == cstr(gle.get('cost_center')) \
			and cstr(e.get('project')) == cstr(gle.get('project')):
				return e

def save_entries(gl_map, adv_adj, update_outstanding, from_repost=False):
	if not from_repost:
		validate_account_for_perpetual_inventory(gl_map)
		
	round_off_debit_credit(gl_map)

	for entry in gl_map:
		make_entry(entry, adv_adj, update_outstanding, from_repost)
		
		# check against budget
		if not from_repost:
			validate_expense_against_budget(entry)
		
		if entry.company == '_Test Company' and entry.cost_center=='Main - WP':
			print(gl_map)
			import traceback
			traceback.print_stack()

def make_entry(args, adv_adj, update_outstanding, from_repost=False):
	args.update({"doctype": "GL Entry"})
	gle = frappe.get_doc(args)
	gle.flags.ignore_permissions = 1
	gle.flags.from_repost = from_repost
	gle.insert()
	gle.run_method("on_update_with_args", adv_adj, update_outstanding, from_repost)
	gle.submit()

def validate_account_for_perpetual_inventory(gl_map):
	if cint(erpnext.is_perpetual_inventory_enabled(gl_map[0].company)) \
		and gl_map[0].voucher_type=="Journal Entry":
			aii_accounts = [d[0] for d in frappe.db.sql("""select name from tabAccount
				where account_type = 'Stock' and is_group=0""")]

			for entry in gl_map:
				if entry.account in aii_accounts:
					frappe.throw(_("Account: {0} can only be updated via Stock Transactions")
						.format(entry.account), StockAccountInvalidTransaction)

def round_off_debit_credit(gl_map):
	precision = get_field_precision(frappe.get_meta("GL Entry").get_field("debit"),
		currency=frappe.db.get_value("Company", gl_map[0].company, "default_currency", cache=True))

	debit_credit_diff = 0.0
	for entry in gl_map:
		entry.debit = flt(entry.debit, precision)
		entry.credit = flt(entry.credit, precision)
		debit_credit_diff += entry.debit - entry.credit

	debit_credit_diff = flt(debit_credit_diff, precision)
	
	if gl_map[0]["voucher_type"] in ("Journal Entry", "Payment Entry"):
		allowance = 5.0 / (10**precision)
	else:
		allowance = .5
	
	if abs(debit_credit_diff) >= allowance:
		frappe.throw(_("Debit and Credit not equal for {0} #{1}. Difference is {2}.")
			.format(gl_map[0].voucher_type, gl_map[0].voucher_no, debit_credit_diff))

	elif abs(debit_credit_diff) >= (1.0 / (10**precision)):
		make_round_off_gle(gl_map, debit_credit_diff)

def make_round_off_gle(gl_map, debit_credit_diff):
	round_off_account, round_off_cost_center = get_round_off_account_and_cost_center(gl_map[0].company)

	round_off_gle = frappe._dict()
	for k in ["voucher_type", "voucher_no", "company",
		"posting_date", "remarks", "is_opening"]:
			round_off_gle[k] = gl_map[0][k]

	round_off_gle.update({
		"account": round_off_account,
		"debit_in_account_currency": abs(debit_credit_diff) if debit_credit_diff < 0 else 0,
		"credit_in_account_currency": debit_credit_diff if debit_credit_diff > 0 else 0,
		"debit": abs(debit_credit_diff) if debit_credit_diff < 0 else 0,
		"credit": debit_credit_diff if debit_credit_diff > 0 else 0,
		"cost_center": round_off_cost_center,
		"party_type": None,
		"party": None,
		"against_voucher_type": None,
		"against_voucher": None
	})

	gl_map.append(round_off_gle)

def get_round_off_account_and_cost_center(company):
	round_off_account, round_off_cost_center = frappe.db.get_value("Company", company,
		["round_off_account", "round_off_cost_center"]) or [None, None]
	if not round_off_account:
		frappe.throw(_("Please mention Round Off Account in Company"))

	if not round_off_cost_center:
		frappe.throw(_("Please mention Round Off Cost Center in Company"))

	return round_off_account, round_off_cost_center

def delete_gl_entries(gl_entries=None, voucher_type=None, voucher_no=None,
		adv_adj=False, update_outstanding="Yes"):

	from erpnext.accounts.doctype.gl_entry.gl_entry import validate_balance_type, \
		check_freezing_date, update_outstanding_amt, validate_frozen_account

	if not gl_entries:
		gl_entries = frappe.db.sql("""
			select account, posting_date, party_type, party, cost_center, fiscal_year,voucher_type,
			voucher_no, against_voucher_type, against_voucher, cost_center, company
			from `tabGL Entry`
			where voucher_type=%s and voucher_no=%s""", (voucher_type, voucher_no), as_dict=True)

	if gl_entries:
		check_freezing_date(gl_entries[0]["posting_date"], adv_adj)

	frappe.db.sql("""delete from `tabGL Entry` where voucher_type=%s and voucher_no=%s""",
		(voucher_type or gl_entries[0]["voucher_type"], voucher_no or gl_entries[0]["voucher_no"]))

	for entry in gl_entries:
		validate_frozen_account(entry["account"], adv_adj)
		validate_balance_type(entry["account"], adv_adj)
		if not adv_adj:
			validate_expense_against_budget(entry)
		
		if entry.get("against_voucher") and update_outstanding == 'Yes' and not adv_adj:
			update_outstanding_amt(entry["account"], entry.get("party_type"), entry.get("party"), entry.get("against_voucher_type"),
				entry.get("against_voucher"), on_cancel=True)
