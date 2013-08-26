# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import flt, cstr, now
from webnotes.model.doc import Document
from accounts.utils import validate_expense_against_budget

def make_gl_entries(gl_map, cancel=False, adv_adj=False, merge_entries=True, 
		update_outstanding='Yes'):
	if not cancel:
		gl_map = process_gl_map(gl_map, merge_entries)
		save_entries(gl_map, adv_adj, update_outstanding)
	else:
		delete_gl_entries(gl_map, adv_adj, update_outstanding)
		
def process_gl_map(gl_map, merge_entries=True):
	if merge_entries:
		gl_map = merge_similar_entries(gl_map)
	
	for entry in gl_map:
		# round off upto 2 decimal
		entry["debit"] = flt(entry["debit"], 2)
		entry["credit"] = flt(entry["credit"], 2)
	
		# toggle debit, credit if negative entry
		if flt(entry["debit"]) < 0 or flt(entry["credit"]) < 0:
			entry["debit"], entry["credit"] = abs(flt(entry["credit"])), abs(flt(entry["debit"]))
	return gl_map
		
def merge_similar_entries(gl_map):
	merged_gl_map = []
	for entry in gl_map:
		# if there is already an entry in this account then just add it 
		# to that entry
		same_head = check_if_in_list(entry, merged_gl_map)
		if same_head:
			same_head['debit']	= flt(same_head['debit']) + flt(entry['debit'])
			same_head['credit'] = flt(same_head['credit']) + flt(entry['credit'])
		else:
			merged_gl_map.append(entry)
			
	# filter zero debit and credit entries
	merged_gl_map = filter(lambda x: flt(x["debit"])!=0 or flt(x["credit"])!=0, merged_gl_map)
	return merged_gl_map

def check_if_in_list(gle, gl_mqp):
	for e in gl_mqp:
		if e['account'] == gle['account'] and \
				cstr(e.get('against_voucher'))==cstr(gle.get('against_voucher')) \
				and cstr(e.get('against_voucher_type')) == \
					cstr(gle.get('against_voucher_type')) \
				and cstr(e.get('cost_center')) == cstr(gle.get('cost_center')):
			return e

def save_entries(gl_map, adv_adj, update_outstanding):
	total_debit = total_credit = 0.0
	for entry in gl_map:
		make_entry(entry, adv_adj, update_outstanding)
		# check against budget
		validate_expense_against_budget(entry)

		# update total debit / credit
		total_debit += flt(entry["debit"])
		total_credit += flt(entry["credit"])
		
	validate_total_debit_credit(total_debit, total_credit)
	
def make_entry(args, adv_adj, update_outstanding):
	args.update({"doctype": "GL Entry"})
	gle = webnotes.bean([args])
	gle.ignore_permissions = 1
	gle.insert()
	gle.run_method("on_update_with_args", adv_adj, update_outstanding)
	gle.submit()
	
def validate_total_debit_credit(total_debit, total_credit):
	if abs(total_debit - total_credit) > 0.005:
		webnotes.throw(webnotes._("Debit and Credit not equal for this voucher: Diff (Debit) is ") +
		 	cstr(total_debit - total_credit))
		
def delete_gl_entries(gl_entries=None, adv_adj=False, update_outstanding="Yes"):
	from accounts.doctype.gl_entry.gl_entry import check_negative_balance, \
		check_freezing_date, update_outstanding_amt, validate_freezed_account
	if gl_entries:
		check_freezing_date(gl_entries[0]["posting_date"], adv_adj)
	
	webnotes.conn.sql("""delete from `tabGL Entry` where voucher_type=%s and voucher_no=%s""", 
		(gl_entries[0]["voucher_type"], gl_entries[0]["voucher_no"]))
	
	for entry in gl_entries:
		validate_freezed_account(entry["account"], adv_adj)
		check_negative_balance(entry["account"], adv_adj)
		validate_expense_against_budget(entry)
		
		if entry.get("against_voucher") and entry.get("against_voucher_type") != "POS" \
			and update_outstanding == 'Yes':
				update_outstanding_amt(entry["account"], entry.get("against_voucher_type"), 
					entry.get("against_voucher"), on_cancel=True)