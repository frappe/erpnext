# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes
from webnotes.utils import flt, cstr, now
from webnotes.model.doc import Document

def make_gl_entries(gl_map, cancel=False, adv_adj=False, merge_entries=True, 
		update_outstanding='Yes'):
	if merge_entries:
		gl_map = merge_similar_entries(gl_map)
	
	if cancel:
		set_as_cancel(gl_map[0]["voucher_type"], gl_map[0]["voucher_no"])

	check_budget(gl_map, cancel)
	save_entries(gl_map, cancel, adv_adj, update_outstanding)
		
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

	return merged_gl_map

def check_if_in_list(gle, gl_mqp):
	for e in gl_mqp:
		if e['account'] == gle['account'] and \
				cstr(e.get('against_voucher'))==cstr(gle.get('against_voucher')) \
				and cstr(e.get('against_voucher_type')) == \
					cstr(gle.get('against_voucher_type')) \
				and cstr(e.get('cost_center')) == cstr(gle.get('cost_center')):
			return e

def check_budget(gl_map, cancel):
	for gle in gl_map:
		if gle.get('cost_center'):
			#check budget only if account is expense account
			acc_details = webnotes.conn.get_value("Account", gle['account'], 
				['is_pl_account', 'debit_or_credit'])
			if acc_details[0]=="Yes" and acc_details[1]=="Debit":
				webnotes.get_obj('Budget Control').check_budget(gle, cancel)

def save_entries(gl_map, cancel, adv_adj, update_outstanding):
	total_debit = total_credit = 0.0
	def _swap(gle):
		gle.debit, gle.credit = abs(flt(gle.credit)), abs(flt(gle.debit))
			
	for entry in gl_map:
		gle = Document('GL Entry', fielddata=entry)
		
		# round off upto 2 decimal
		gle.debit = flt(gle.debit, 2)
		gle.credit = flt(gle.credit, 2)
		
		# toggle debit, credit if negative entry
		if flt(gle.debit) < 0 or flt(gle.credit) < 0:
			_swap(gle)

		# toggled debit/credit in two separate condition because 
		# both should be executed at the 
		# time of cancellation when there is negative amount (tax discount)
		if cancel:
			_swap(gle)

		gle_obj = webnotes.get_obj(doc=gle)
		# validate except on_cancel
		if not cancel:
			gle_obj.validate()

		# save
		gle.save(1)
		gle_obj.on_update(adv_adj, cancel, update_outstanding)

		# update total debit / credit
		total_debit += flt(gle.debit)
		total_credit += flt(gle.credit)
		
		# print gle.account, gle.debit, gle.credit, total_debit, total_credit
		
	if not cancel:
		validate_total_debit_credit(total_debit, total_credit)
	
def validate_total_debit_credit(total_debit, total_credit):
	if abs(total_debit - total_credit) > 0.005:
		webnotes.msgprint("""Debit and Credit not equal for 
			this voucher: Diff (Debit) is %s""" %
		 	(total_debit - total_credit), raise_exception=1)

def set_as_cancel(voucher_type, voucher_no):
	webnotes.conn.sql("""update `tabGL Entry` set is_cancelled='Yes',
		modified=%s, modified_by=%s
		where voucher_type=%s and voucher_no=%s""", 
		(now(), webnotes.session.user, voucher_type, voucher_no))