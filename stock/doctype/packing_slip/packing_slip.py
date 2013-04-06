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
from webnotes.utils import flt, cint, now

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl


	def validate(self):
		"""
			* Validate existence of submitted Delivery Note
			* Case nos do not overlap
			* Check if packed qty doesn't exceed actual qty of delivery note

			It is necessary to validate case nos before checking quantity
		"""
		self.validate_delivery_note()
		self.validate_case_nos()
		self.validate_qty()


	def validate_delivery_note(self):
		"""
			Validates if delivery note has status as submitted
		"""
		res = webnotes.conn.sql("""SELECT docstatus FROM `tabDelivery Note` 
			WHERE name=%(delivery_note)s""", self.doc.fields)

		if not(res and res[0][0]==0):
			webnotes.msgprint("""Invalid Delivery Note. Delivery Note should exist 
				and should be in draft state. Please rectify and try again.""", raise_exception=1)


	def validate_case_nos(self):
		"""
			Validate if case nos overlap
			If they do, recommend next case no.
		"""
		if not cint(self.doc.from_case_no):
			webnotes.msgprint("Please specify a valid 'From Case No.'", raise_exception=1)
		elif not self.doc.to_case_no:
			self.doc.to_case_no = self.doc.from_case_no
		elif self.doc.from_case_no > self.doc.to_case_no:
			webnotes.msgprint("'To Case No.' cannot be less than 'From Case No.'",
				raise_exception=1)
		
		
		res = webnotes.conn.sql("""SELECT name FROM `tabPacking Slip`
			WHERE delivery_note = %(delivery_note)s AND docstatus = 1 AND
			(from_case_no BETWEEN %(from_case_no)s AND %(to_case_no)s
			OR to_case_no BETWEEN %(from_case_no)s AND %(to_case_no)s)
			""", self.doc.fields)

		if res:
			webnotes.msgprint("""Case No(s). already in use. Please rectify and try again.
				Recommended <b>From Case No. = %s</b>""" % self.get_recommended_case_no(),
				raise_exception=1)


	def validate_qty(self):
		"""
			Check packed qty across packing slips and delivery note
		"""
		# Get Delivery Note Items, Item Quantity Dict and No. of Cases for this Packing slip
		dn_details, ps_item_qty, no_of_cases = self.get_details_for_packing()

		for item in dn_details:
			new_packed_qty = (flt(ps_item_qty[item['item_code']]) * no_of_cases) + flt(item['packed_qty'])
			if new_packed_qty > flt(item['qty']):
				self.recommend_new_qty(item, ps_item_qty, no_of_cases)


	def get_details_for_packing(self):
		"""
			Returns
			* 'Delivery Note Items' query result as a list of dict
			* Item Quantity dict of current packing slip doc
			* No. of Cases of this packing slip
		"""
		item_codes = ", ".join([('"' + d.item_code + '"') for d in
			self.doclist])
		
		items = [d.item_code for d in self.doclist.get({"parentfield": "item_details"})]
		
		if not item_codes: webnotes.msgprint("No Items to Pack",
				raise_exception=1)
		
		# gets item code, qty per item code, latest packed qty per item code and stock uom
		res = webnotes.conn.sql("""select item_code, ifnull(sum(qty), 0) as qty,
			(select sum(ifnull(psi.qty, 0) * (abs(ps.to_case_no - ps.from_case_no) + 1))
				from `tabPacking Slip` ps, `tabPacking Slip Item` psi
				where ps.name = psi.parent and ps.docstatus = 1
				and ps.delivery_note = dni.parent and psi.item_code=dni.item_code)
					as packed_qty,
			stock_uom
			from `tabDelivery Note Item` dni
			where parent=%s and item_code in (%s)
			group by item_code""" % ("%s", ", ".join(["%s"]*len(items))),
			tuple([self.doc.delivery_note] + items), as_dict=1)
			
		ps_item_qty = dict([[d.item_code, d.qty] for d in self.doclist])

		no_of_cases = cint(self.doc.to_case_no) - cint(self.doc.from_case_no) + 1

		return res, ps_item_qty, no_of_cases


	def recommend_new_qty(self, item, ps_item_qty, no_of_cases):
		"""
			Recommend a new quantity and raise a validation exception
		"""
		item['recommended_qty'] = (flt(item['qty']) - flt(item['packed_qty'])) / no_of_cases
		item['specified_qty'] = flt(ps_item_qty[item['item_code']])
		if not item['packed_qty']: item['packed_qty'] = 0
		
		webnotes.msgprint("""
			Invalid Quantity specified (%(specified_qty)s %(stock_uom)s).
			%(packed_qty)s out of %(qty)s %(stock_uom)s already packed for %(item_code)s.
			<b>Recommended quantity for %(item_code)s = %(recommended_qty)s 
			%(stock_uom)s</b>""" % item, raise_exception=1)


	def on_submit(self):
		"""
			* Update packed qty for all items
		"""
		self.update_packed_qty(event='submit')


	def on_cancel(self):
		"""
			* Update packed qty for all items
		"""
		self.update_packed_qty(event='cancel')


	def update_packed_qty(self, event=''):
		"""
			Updates packed qty for all items
		"""
		if event not in ['submit', 'cancel']:
			raise Exception('update_packed_quantity can only be called on submit or cancel')

		# Get Delivery Note Items, Item Quantity Dict and No. of Cases for this Packing slip
		dn_details, ps_item_qty, no_of_cases = self.get_details_for_packing()

		for item in dn_details:
			new_packed_qty = flt(item['packed_qty'])
			if (new_packed_qty < 0) or (new_packed_qty > flt(item['qty'])):
				webnotes.msgprint("""Invalid new packed quantity for item %s. 
					Please try again or contact support@erpnext.com""" % 
					item['item_code'], raise_exception=1)
			
			webnotes.conn.sql("""UPDATE `tabDelivery Note Item`
				SET packed_qty = %s WHERE parent = %s AND item_code = %s""",
				(new_packed_qty, self.doc.delivery_note, item['item_code']))
				
			webnotes.conn.set_value("Delivery Note", self.doc.delivery_note, "modified", now())


	def update_item_details(self):
		"""
			Fill empty columns in Packing Slip Item
		"""
		if not self.doc.from_case_no:
			self.doc.from_case_no = self.get_recommended_case_no()

		for d in self.doclist.get({"parentfield": "item_details"}):
			self.set_item_details(d)


	def set_item_details(self, row):
		res = webnotes.conn.sql("""SELECT item_name, SUM(IFNULL(qty, 0)) as total_qty,
			IFNULL(packed_qty,	0) as packed_qty, stock_uom
			FROM `tabDelivery Note Item`
			WHERE parent=%s AND item_code=%s GROUP BY item_code""",
			(self.doc.delivery_note, row.item_code), as_dict=1)

		if res and len(res)>0:
			qty = res[0]['total_qty'] - res[0]['packed_qty']
			if not row.qty:
				row.qty = qty >= 0 and qty or 0

		res = webnotes.conn.sql("""SELECT net_weight, weight_uom FROM `tabItem`
			WHERE name=%s""", row.item_code, as_dict=1)
			
		if res and len(res)>0:
			row.net_weight = res[0]["net_weight"]
			row.weight_uom = res[0]["weight_uom"]


	def get_recommended_case_no(self):
		"""
			Returns the next case no. for a new packing slip for a delivery
			note
		"""
		recommended_case_no = webnotes.conn.sql("""SELECT MAX(to_case_no) FROM `tabPacking Slip`
			WHERE delivery_note = %(delivery_note)s AND docstatus=1""", self.doc.fields)

		return cint(recommended_case_no[0][0]) + 1