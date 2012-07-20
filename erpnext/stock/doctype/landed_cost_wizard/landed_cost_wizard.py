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

import webnotes
from webnotes.utils import cint, cstr, flt
from webnotes.model.doc import addchild, getchildren
from webnotes.model.doclist import getlist
from webnotes.model.code import get_obj
from webnotes import msgprint

sql = webnotes.conn.sql

# -----------------------------------------------------------------------------------------

class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		self.prwise_cost = {}
		
	def check_mandatory(self):
		""" Check mandatory fields """		
		if not self.doc.from_pr_date or not self.doc.to_pr_date:
			msgprint("Please enter From and To PR Date", raise_exception=1)

		if not self.doc.currency:
			msgprint("Please enter Currency.", raise_exception=1)


	def get_purchase_receipts(self):
		"""	Get purchase receipts for given period """
				
		self.doclist = self.doc.clear_table(self.doclist,'lc_pr_details',1)
		self.check_mandatory()
		
		pr = sql("select name from `tabPurchase Receipt` where docstatus = 1 and posting_date >= '%s' and posting_date <= '%s' and currency = '%s' order by name " % (self.doc.from_pr_date, self.doc.to_pr_date, self.doc.currency), as_dict = 1)
		if len(pr)>200:
			msgprint("Please enter date of shorter duration as there are too many purchase receipt, hence it cannot be loaded.", raise_exception=1)
			
		for i in pr:
			ch = addchild(self.doc, 'lc_pr_details', 'Landed Cost Purchase Receipt', 1, self.doclist)
			ch.purchase_receipt = i and i['name'] or ''
			ch.save()


	def get_landed_cost_master_details(self):
		""" pull details from landed cost master"""
		self.doclist = self.doc.clear_table(self.doclist, 'landed_cost_details')
		idx = 0
		landed_cost = sql("select account_head, description from `tabLanded Cost Master Detail` where parent=%s", (self.doc.landed_cost), as_dict = 1)
		for cost in landed_cost:
			lct = addchild(self.doc, 'landed_cost_details', 'Landed Cost Item', 1, self.doclist)
			lct.account_head = cost['account_head']
			lct.description = cost['description']


	def get_selected_pr(self):
		""" Get selected purchase receipt no """
		self.selected_pr = [d.purchase_receipt for d in getlist(self.doclist, 'lc_pr_details') if d.select_pr]
		if not self.selected_pr:
			msgprint("Please select atleast one PR to proceed.", raise_exception=1)
		
	def validate_selected_pr(self):
		"""Validate selected PR as submitted"""
		invalid_pr =  sql("SELECT name FROM `tabPurchase Receipt` WHERE docstatus != 1 and name in (%s)" % ("'" + "', '".join(self.selected_pr) + "'"))
		if invalid_pr:
			msgprint("Selected purchase receipts must be submitted. Following PR are not submitted: %s" % invalid_pr, raise_exception=1)
			

	def get_total_amt(self):
		""" Get sum of net total of all selected PR"""		
		return sql("SELECT SUM(net_total) FROM `tabPurchase Receipt` WHERE name in (%s)" % ("'" + "', '".join(self.selected_pr) + "'"))[0][0]
		

	def add_charges_in_pr(self):
		""" Add additional charges in selected pr proportionately"""
		total_amt = self.get_total_amt()
		
		for pr in self.selected_pr:
			pr_obj = get_obj('Purchase Receipt', pr, with_children = 1)
			cumulative_grand_total = flt(pr_obj.doc.grand_total)
			
			for lc in getlist(self.doclist, 'landed_cost_details'):
				amt = flt(lc.amount) * flt(pr_obj.doc.net_total)/ flt(total_amt)
				self.prwise_cost[pr] = self.prwise_cost.get(pr, 0) + amt
				cumulative_grand_total += amt
				
				pr_oc_row = sql("select name from `tabPurchase Taxes and Charges` where parent = %s and category = 'For Valuation' and add_deduct_tax = 'Add' and charge_type = 'Actual' and account_head = %s",(pr, lc.account_head))
				if not pr_oc_row:	# add if not exists
					ch = addchild(pr_obj.doc, 'purchase_tax_details', 'Purchase Taxes and Charges', 1)
					ch.category = 'For Valuation'
					ch.add_deduct_tax = 'Add'
					ch.charge_type = 'Actual'
					ch.description = lc.description
					ch.account_head = lc.account_head
					ch.rate = amt
					ch.tax_amount = amt
					ch.total = cumulative_grand_total
					ch.docstatus = 1
					ch.idx = 500 # add at the end
					ch.save(1)
				else:	# overwrite if exists
					sql("update `tabPurchase Taxes and Charges` set rate = %s, tax_amount = %s where name = %s and parent = %s ", (amt, amt, pr_oc_row[0][0], pr))
		
		
	def reset_other_charges(self, pr_obj):
		""" Reset all calculated values to zero"""
		for t in getlist(pr_obj.doclist, 'purchase_tax_details'):
			t.total_tax_amount = 0;
			t.total_amount = 0;
			t.tax_amount = 0;
			t.total = 0;
			t.save()
			
		
	def cal_charges_and_item_tax_amt(self):
		""" Re-calculates other charges values and itemwise tax amount for getting valuation rate"""
		import json
		for pr in self.selected_pr:
			obj = get_obj('Purchase Receipt', pr, with_children = 1)
			total = 0
			self.reset_other_charges(obj)

			for prd in getlist(obj.doclist, 'purchase_receipt_details'):
				prev_total, item_tax = flt(prd.amount), 0
				total += flt(prd.qty) * flt(prd.purchase_rate)
			
				try:
					item_tax_rate = prd.item_tax_rate and json.loads(prd.item_tax_rate) or {}
				except ValueError:
					item_tax_rate = prd.item_tax_rate and eval(prd.item_tax_rate) or {}

				
				ocd = getlist(obj.doclist, 'purchase_tax_details')
				# calculate tax for other charges
				for oc in range(len(ocd)):
					# Get rate : consider if diff for this item
					if item_tax_rate.get(ocd[oc].account_head) and ocd[oc].charge_type != 'Actual':
						rate = item_tax_rate[ocd[oc].account_head]
					else:
						rate = flt(ocd[oc].rate)
				
					tax_amount = self.cal_tax(ocd, prd, rate, obj.doc.net_total, oc)					
					total, prev_total, item_tax = self.add_deduct_taxes(ocd, oc, tax_amount, total, prev_total, item_tax)

				prd.item_tax_amount = flt(item_tax)
				prd.save()
			obj.doc.save()
	
	
	def cal_tax(self, ocd, prd, rate, net_total, oc):
		""" Calculates tax amount for one item"""
		tax_amount = 0
		if ocd[oc].charge_type == 'Actual':
			tax_amount = flt(rate) * flt(prd.amount) / flt(net_total)
		elif ocd[oc].charge_type == 'On Net Total':
			tax_amount = flt(rate) * flt(prd.amount) / 100		
		elif ocd[oc].charge_type == 'On Previous Row Amount':			
			row_no = cstr(ocd[oc].row_id)
			row = row_no.split("+")
			for r in range(0, len(row)):
				id = cint(row[r])
				tax_amount += flt((flt(rate) * flt(ocd[id-1].total_amount) / 100))
			row_id = row_no.find("/")
			if row_id != -1:
				rate = ''
				row = (row_no).split("/")				
				id1 = cint(row[0])
				id2 = cint(row[1])
				tax_amount = flt(flt(ocd[id1-1].total_amount) / flt(ocd[id2-1].total_amount))
		elif ocd[oc].charge_type == 'On Previous Row Total':
			row = cint(ocd[oc].row_id)
			if ocd[row-1].add_deduct_tax == 'Add':
			  tax_amount = flt(rate) * (flt(ocd[row-1].total_tax_amount)+flt(ocd[row-1].total_amount)) / 100
			elif ocd[row-1].add_deduct_tax == 'Deduct':
			  tax_amount = flt(rate) * (flt(ocd[row-1].total_tax_amount)-flt(ocd[row-1].total_amount)) / 100
		
		return tax_amount  

	def add_deduct_taxes(self, ocd, oc, tax_amount, total, prev_total, item_tax):
		"""Calculates other charges values"""
		add_ded = ocd[oc].add_deduct_tax == 'Add' and 1 or ocd[oc].add_or_deduct == 'Deduct' and -1
		ocd[oc].total_amount = flt(tax_amount)
		ocd[oc].total_tax_amount = flt(prev_total)
		ocd[oc].tax_amount += flt(tax_amount)
		
		total_amount = flt(ocd[oc].tax_amount)
		total_tax_amount = flt(ocd[oc].total_tax_amount) + (add_ded * flt(total_amount))
		
		if ocd[oc].category != "For Valuation":	
			prev_total += add_ded * flt(ocd[oc].total_amount)
			total += add_ded * flt(ocd[oc].tax_amount)
			ocd[oc].total = total
		else:
			prev_total = prev_total
			ocd[oc].total = flt(total)
		ocd[oc].save()
				
		if ocd[oc].category != "For Total":
			item_tax += add_ded * ocd[oc].total_amount
		
		return total, prev_total, item_tax


	def update_sle(self):
		""" Recalculate valuation rate in all sle after pr posting date"""
		for pr in self.selected_pr:
			pr_obj = get_obj('Purchase Receipt', pr, with_children = 1)
			
			for d in getlist(pr_obj.doclist, 'purchase_receipt_details'):
				if flt(d.qty):
					d.valuation_rate = (flt(d.purchase_rate) + (flt(d.rm_supp_cost)/flt(d.qty)) + (flt(d.item_tax_amount)/flt(d.qty))) / flt(d.conversion_factor)
					d.save()
					self.update_serial_no(d.serial_no, d.valuation_rate)
				sql("update `tabStock Ledger Entry` set incoming_rate = '%s' where voucher_detail_no = '%s'"%(flt(d.valuation_rate), d.name))
				
				bin = sql("select t1.name, t2.posting_date, t2.posting_time from `tabBin` t1, `tabStock Ledger Entry` t2 where t2.voucher_detail_no = '%s' and t2.item_code = t1.item_code and t2.warehouse = t1.warehouse LIMIT 1" % d.name)

				# update valuation rate after pr posting date
				if bin and bin[0][0]:
					obj = get_obj('Bin', bin[0][0]).update_entries_after(bin[0][1], bin[0][2])

	
	def update_serial_no(self, sr_no, rate):
		""" update valuation rate in serial no"""
		sr_no = cstr(sr_no).split('\n')
		for d in sr_no:
			sql("update `tabSerial No` set purchase_rate = %s where name = %s", (rate, d))

				
	def update_landed_cost(self):
		""" 
			Add extra cost and recalculate all values in pr, 
			Recalculate valuation rate in all sle after pr posting date
		"""	
		self.get_selected_pr()
		self.validate_selected_pr()			
		self.add_charges_in_pr()		
		self.cal_charges_and_item_tax_amt()
		self.update_sle()
		msgprint("Landed Cost updated successfully")
