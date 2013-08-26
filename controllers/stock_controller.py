# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cint, flt, cstr
from webnotes import msgprint, _
import webnotes.defaults

from controllers.accounts_controller import AccountsController

class StockController(AccountsController):
	def make_gl_entries(self):
		if not cint(webnotes.defaults.get_global_default("perpetual_accounting")):
			return
		
		from accounts.general_ledger import make_gl_entries, delete_gl_entries
		gl_entries = self.get_gl_entries_for_stock()
		
		if gl_entries and self.doc.docstatus==1:
			make_gl_entries(gl_entries)
		elif self.doc.docstatus==2:
			webnotes.conn.sql("""delete from `tabGL Entry` where voucher_type=%s 
				and voucher_no=%s""", (self.doc.doctype, self.doc.name))
			
		self.update_gl_entries_after()
			
			
	def get_gl_entries_for_stock(self, item_acc_map=None, expense_account=None, cost_center=None):
		from accounts.general_ledger import process_gl_map

		if not (expense_account or cost_center or item_acc_map):
			item_acc_map = {}
			for item in self.doclist.get({"parentfield": self.fname}):
				self.check_expense_account(item)
				item_acc_map.setdefault(item.name, [item.expense_account, item.cost_center])
		
		gl_entries = []
		stock_value_diff = self.get_stock_value_diff_from_sle(item_acc_map, expense_account, 
			cost_center)
		for stock_in_hand_account, against_stock_account_dict in stock_value_diff.items():
			for against_stock_account, cost_center_dict in against_stock_account_dict.items():
				for cost_center, value_diff in cost_center_dict.items():
					gl_entries += [
						# stock in hand account
						self.get_gl_dict({
							"account": stock_in_hand_account,
							"against": against_stock_account,
							"debit": value_diff,
							"remarks": self.doc.remarks or "Accounting Entry for Stock",
						}),
			
						# account against stock in hand
						self.get_gl_dict({
							"account": against_stock_account,
							"against": stock_in_hand_account,
							"credit": value_diff,
							"cost_center": cost_center != "No Cost Center" and cost_center or None,
							"remarks": self.doc.remarks or "Accounting Entry for Stock",
						}),
					]
		gl_entries = process_gl_map(gl_entries)
		return gl_entries
		
			
	def get_stock_value_diff_from_sle(self, item_acc_map, expense_account, cost_center):
		wh_acc_map = self.get_warehouse_account_map()
		stock_value_diff = {}
		for sle in webnotes.conn.sql("""select warehouse, stock_value_difference, voucher_detail_no
			from `tabStock Ledger Entry` where voucher_type=%s and voucher_no=%s""",
			(self.doc.doctype, self.doc.name), as_dict=True):
				account = wh_acc_map[sle.warehouse]
				against_account = expense_account or item_acc_map[sle.voucher_detail_no][0]
				cost_center = cost_center or item_acc_map[sle.voucher_detail_no][1] or \
					"No Cost Center"
				
				stock_value_diff.setdefault(account, {}).setdefault(against_account, {})\
					.setdefault(cost_center, 0)
				stock_value_diff[account][against_account][cost_center] += \
					flt(sle.stock_value_difference)
				 
		return stock_value_diff
		
	def get_warehouse_account_map(self):
		wh_acc_map = {}
		warehouse_with_no_account = []
		for d in webnotes.conn.sql("""select name, account from `tabWarehouse`""", as_dict=True):
			if not d.account: warehouse_with_no_account.append(d.name)
			wh_acc_map.setdefault(d.name, d.account)
			
		if warehouse_with_no_account:
			webnotes.throw(_("Please mention Perpetual Account in warehouse master for \
				following warehouses") + ": " + '\n'.join(warehouse_with_no_account))
				
		return wh_acc_map
		
	def update_gl_entries_after(self):
		future_stock_vouchers = self.get_future_stock_vouchers()
		gle = self.get_voucherwise_gl_entries(future_stock_vouchers)
		for voucher_type, voucher_no in future_stock_vouchers:
			existing_gle = gle.get((voucher_type, voucher_no), {})
			voucher_bean = webnotes.bean(voucher_type, voucher_no)
			expected_gle = voucher_bean.run_method("get_gl_entries_for_stock")
			if expected_gle:
				if existing_gle:
					matched = True
					for entry in expected_gle:
						entry_amount = existing_gle.get(entry.account, {}).get(entry.cost_center \
							or "No Cost Center", [0, 0])
					
						if [entry.debit, entry.credit] != entry_amount:
							matched = False
							break
					
					if not matched:
						# make updated entry
						webnotes.conn.sql("""delete from `tabGL Entry` 
							where voucher_type=%s and voucher_no=%s""", (voucher_type, voucher_no))
					
						voucher_bean.run_method("make_gl_entries")
				else:
					# make adjustment entry on that date
					self.make_adjustment_entry(expected_gle, voucher_bean)
				
		
	def get_future_stock_vouchers(self):
		future_stock_vouchers = []
		for d in webnotes.conn.sql("""select distinct voucher_type, voucher_no 
			from `tabStock Ledger Entry` 
			where timestamp(posting_date, posting_time) >= timestamp(%s, %s)
			order by timestamp(posting_date, posting_time) asc, name asc""", 
			(self.doc.posting_date, self.doc.posting_time), as_dict=True):
				future_stock_vouchers.append([d.voucher_type, d.voucher_no])
				
		return future_stock_vouchers
				
	def get_voucherwise_gl_entries(self, future_stock_vouchers):
		gl_entries = {}
		if future_stock_vouchers:
			for d in webnotes.conn.sql("""select * from `tabGL Entry` 
				where posting_date >= %s and voucher_no in (%s)""" % 
				('%s', ', '.join(['%s']*len(future_stock_vouchers))), 
				tuple([self.doc.posting_date] + [d[1] for d in future_stock_vouchers]), as_dict=1):
					gl_entries.setdefault((d.voucher_type, d.voucher_no), {})\
						.setdefault(d.account, {})\
						.setdefault(d.cost_center, [d.debit, d.credit])
		
		return gl_entries
					
	def make_adjustment_entry(self, expected_gle, voucher_bean):
		from accounts.utils import get_stock_and_account_difference
		account_list = [d.account for d in expected_gle]
		acc_diff = get_stock_and_account_difference(account_list, expected_gle[0].posting_date)
		
		cost_center = self.get_company_default("cost_center")
		stock_adjustment_account = self.get_company_default("stock_adjustment_account")

		gl_entries = []
		for account, diff in acc_diff.items():
			if diff:
				gl_entries.append([
					# stock in hand account
					voucher_bean.get_gl_dict({
						"account": account,
						"against": stock_adjustment_account,
						"debit": diff,
						"remarks": "Adjustment Accounting Entry for Stock",
					}),
				
					# account against stock in hand
					voucher_bean.get_gl_dict({
						"account": stock_adjustment_account,
						"against": account,
						"credit": diff,
						"cost_center": cost_center or None,
						"remarks": "Adjustment Accounting Entry for Stock",
					}),
				])
				
		if gl_entries:
			from accounts.general_ledger import make_gl_entries
			make_gl_entries(gl_entries)
			
	def check_expense_account(self, item):
		if item.fields.has_key("expense_account") and not item.expense_account:
			msgprint(_("""Expense account is mandatory for item: """) + item.item_code, 
				raise_exception=1)
				
		if item.fields.has_key("expense_account") and not item.cost_center:
			msgprint(_("""Cost Center is mandatory for item: """) + item.item_code, 
				raise_exception=1)
				
	def get_sl_entries(self, d, args):		
		sl_dict = {
			"item_code": d.item_code,
			"warehouse": d.warehouse,
			"posting_date": self.doc.posting_date,
			"posting_time": self.doc.posting_time,
			"voucher_type": self.doc.doctype,
			"voucher_no": self.doc.name,
			"voucher_detail_no": d.name,
			"actual_qty": (self.doc.docstatus==1 and 1 or -1)*flt(d.stock_qty),
			"stock_uom": d.stock_uom,
			"incoming_rate": 0,
			"company": self.doc.company,
			"fiscal_year": self.doc.fiscal_year,
			"batch_no": cstr(d.batch_no).strip(),
			"serial_no": d.serial_no,
			"project": d.project_name,
			"is_cancelled": self.doc.docstatus==2 and "Yes" or "No"
		}
		
		sl_dict.update(args)
		return sl_dict
		
	def make_sl_entries(self, sl_entries, is_amended=None):
		from stock.stock_ledger import make_sl_entries
		make_sl_entries(sl_entries, is_amended)
		
	def get_stock_ledger_entries(self, item_list=None, warehouse_list=None):
		out = {}
		
		if not (item_list and warehouse_list):
			item_list, warehouse_list = self.get_distinct_item_warehouse()
			
		if item_list and warehouse_list:
			res = webnotes.conn.sql("""select item_code, voucher_type, voucher_no,
				voucher_detail_no, posting_date, posting_time, stock_value,
				warehouse, actual_qty as qty from `tabStock Ledger Entry` 
				where company = %s and item_code in (%s) and warehouse in (%s)
				order by item_code desc, warehouse desc, posting_date desc, 
				posting_time desc, name desc""" % 
				('%s', ', '.join(['%s']*len(item_list)), ', '.join(['%s']*len(warehouse_list))), 
				tuple([self.doc.company] + item_list + warehouse_list), as_dict=1)
				
			for r in res:
				if (r.item_code, r.warehouse) not in out:
					out[(r.item_code, r.warehouse)] = []
		
				out[(r.item_code, r.warehouse)].append(r)

		return out

	def get_distinct_item_warehouse(self):
		item_list = []
		warehouse_list = []
		for item in self.doclist.get({"parentfield": self.fname}) \
				+ self.doclist.get({"parentfield": "packing_details"}):
			item_list.append(item.item_code)
			warehouse_list.append(item.warehouse)
			
		return list(set(item_list)), list(set(warehouse_list))
		
	def make_cancel_gl_entries(self):
		if webnotes.conn.sql("""select name from `tabGL Entry` where voucher_type=%s 
			and voucher_no=%s""", (self.doc.doctype, self.doc.name)):
				self.make_gl_entries()