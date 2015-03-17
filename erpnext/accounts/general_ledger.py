# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, cstr
from frappe import _
from erpnext.accounts.utils import validate_expense_against_budget


class StockAccountInvalidTransaction(frappe.ValidationError): pass

def make_gl_entries(gl_map, cancel=False, adv_adj=False, merge_entries=True,
		update_outstanding='Yes'):
	if gl_map:
		if not cancel:
			gl_map = process_gl_map(gl_map, merge_entries)
			if gl_map and len(gl_map) > 1:
				save_entries(gl_map, adv_adj, update_outstanding)
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
		if flt(entry.credit) < 0:
			entry.debit = flt(entry.debit) - flt(entry.credit)
			entry.credit = 0.0

	return gl_map

def merge_similar_entries(gl_map):
	merged_gl_map = []
	for entry in gl_map:
		# if there is already an entry in this account then just add it
		# to that entry
		same_head = check_if_in_list(entry, merged_gl_map)
		if same_head:
			same_head.debit	= flt(same_head.debit) + flt(entry.debit)
			same_head.credit = flt(same_head.credit) + flt(entry.credit)
		else:
			merged_gl_map.append(entry)

	# filter zero debit and credit entries
	merged_gl_map = filter(lambda x: flt(x.debit)!=0 or flt(x.credit)!=0, merged_gl_map)
	return merged_gl_map

def check_if_in_list(gle, gl_map):
	for e in gl_map:
		if e.account == gle.account and \
				cstr(e.get('against_voucher'))==cstr(gle.get('against_voucher')) \
				and cstr(e.get('against_voucher_type')) == \
					cstr(gle.get('against_voucher_type')) \
				and cstr(e.get('cost_center')) == cstr(gle.get('cost_center')):
			return e

def save_entries(gl_map, adv_adj, update_outstanding):
	validate_account_for_auto_accounting_for_stock(gl_map)

	total_debit = total_credit = 0.0
	for entry in gl_map:
		make_entry(entry, adv_adj, update_outstanding)
		# check against budget
		validate_expense_against_budget(entry)


		# update total debit / credit
		total_debit += flt(entry.debit)
		total_credit += flt(entry.credit)

	validate_total_debit_credit(total_debit, total_credit)

def make_entry(args, adv_adj, update_outstanding):
	args.update({"doctype": "GL Entry"})
	gle = frappe.get_doc(args)
	gle.flags.ignore_permissions = 1
	gle.insert()
	gle.run_method("on_update_with_args", adv_adj, update_outstanding)
	gle.submit()

def validate_total_debit_credit(total_debit, total_credit):
	if abs(total_debit - total_credit) > 0.005:
		frappe.throw(_("Debit and Credit not equal for this voucher. Difference is {0}.").format(total_debit - total_credit))

def validate_account_for_auto_accounting_for_stock(gl_map):
	if gl_map[0].voucher_type=="Journal Entry":
		aii_accounts = [d[0] for d in frappe.db.sql("""select name from tabAccount
			where account_type = 'Warehouse' and ifnull(warehouse, '')!=''""")]

		for entry in gl_map:
			if entry.account in aii_accounts:
				frappe.throw(_("Account: {0} can only be updated via Stock Transactions").format(entry.account), StockAccountInvalidTransaction)


def delete_gl_entries(gl_entries=None, voucher_type=None, voucher_no=None,
		adv_adj=False, update_outstanding="Yes"):

	from erpnext.accounts.doctype.gl_entry.gl_entry import validate_balance_type, \
		check_freezing_date, update_outstanding_amt, validate_frozen_account

	if not gl_entries:
		gl_entries = frappe.db.sql("""select * from `tabGL Entry`
			where voucher_type=%s and voucher_no=%s""", (voucher_type, voucher_no), as_dict=True)
	if gl_entries:
		check_freezing_date(gl_entries[0]["posting_date"], adv_adj)

	frappe.db.sql("""delete from `tabGL Entry` where voucher_type=%s and voucher_no=%s""",
		(voucher_type or gl_entries[0]["voucher_type"], voucher_no or gl_entries[0]["voucher_no"]))

	for entry in gl_entries:
		validate_frozen_account(entry["account"], adv_adj)
		validate_balance_type(entry["account"], adv_adj)
		validate_expense_against_budget(entry)

		if entry.get("against_voucher") and update_outstanding == 'Yes':
			update_outstanding_amt(entry["account"], entry.get("party_type"), entry.get("party"), entry.get("against_voucher_type"),
				entry.get("against_voucher"), on_cancel=True)
