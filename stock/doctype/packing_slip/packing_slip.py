# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import flt, cint
from webnotes import msgprint, _
from webnotes.model.doc import addchild

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
		self.validate_items_mandatory()
		self.validate_case_nos()
		self.validate_qty()

		from utilities.transaction_base import validate_uom_is_integer
		validate_uom_is_integer(self.doclist, "stock_uom", "qty")
		validate_uom_is_integer(self.doclist, "weight_uom", "net_weight")

	def validate_delivery_note(self):
		"""
			Validates if delivery note has status as draft
		"""
		if cint(webnotes.conn.get_value("Delivery Note", self.doc.delivery_note, "docstatus")) != 0:
			msgprint(_("""Invalid Delivery Note. Delivery Note should exist and should be in 
				draft state. Please rectify and try again."""), raise_exception=1)
	
	def validate_items_mandatory(self):
		rows = [d.item_code for d in self.doclist.get({"parentfield": "item_details"})]
		if not rows:
			webnotes.msgprint(_("No Items to Pack"), raise_exception=1)

	def validate_case_nos(self):
		"""
			Validate if case nos overlap. If they do, recommend next case no.
		"""
		if not cint(self.doc.from_case_no):
			webnotes.msgprint(_("Please specify a valid 'From Case No.'"), raise_exception=1)
		elif not self.doc.to_case_no:
			self.doc.to_case_no = self.doc.from_case_no
		elif self.doc.from_case_no > self.doc.to_case_no:
			webnotes.msgprint(_("'To Case No.' cannot be less than 'From Case No.'"),
				raise_exception=1)
		
		
		res = webnotes.conn.sql("""SELECT name FROM `tabPacking Slip`
			WHERE delivery_note = %(delivery_note)s AND docstatus = 1 AND
			(from_case_no BETWEEN %(from_case_no)s AND %(to_case_no)s
			OR to_case_no BETWEEN %(from_case_no)s AND %(to_case_no)s
			OR %(from_case_no)s BETWEEN from_case_no AND to_case_no)
			""", self.doc.fields)

		if res:
			webnotes.msgprint(_("""Case No(s) already in use. Please rectify and try again.
				Recommended <b>From Case No. = %s</b>""") % self.get_recommended_case_no(),
				raise_exception=1)

	def validate_qty(self):
		"""
			Check packed qty across packing slips and delivery note
		"""
		# Get Delivery Note Items, Item Quantity Dict and No. of Cases for this Packing slip
		dn_details, ps_item_qty, no_of_cases = self.get_details_for_packing()

		for item in dn_details:
			new_packed_qty = (flt(ps_item_qty[item['item_code']]) * no_of_cases) + \
			 	flt(item['packed_qty'])
			if new_packed_qty > flt(item['qty']) and no_of_cases:
				self.recommend_new_qty(item, ps_item_qty, no_of_cases)


	def get_details_for_packing(self):
		"""
			Returns
			* 'Delivery Note Items' query result as a list of dict
			* Item Quantity dict of current packing slip doc
			* No. of Cases of this packing slip
		"""
		
		rows = [d.item_code for d in self.doclist.get({"parentfield": "item_details"})]
		
		condition = ""
		if rows:
			condition = " and item_code in (%s)" % (", ".join(["%s"]*len(rows)))
		
		# gets item code, qty per item code, latest packed qty per item code and stock uom
		res = webnotes.conn.sql("""select item_code, ifnull(sum(qty), 0) as qty,
			(select sum(ifnull(psi.qty, 0) * (abs(ps.to_case_no - ps.from_case_no) + 1))
				from `tabPacking Slip` ps, `tabPacking Slip Item` psi
				where ps.name = psi.parent and ps.docstatus = 1
				and ps.delivery_note = dni.parent and psi.item_code=dni.item_code) as packed_qty,
			stock_uom, item_name
			from `tabDelivery Note Item` dni
			where parent=%s %s 
			group by item_code""" % ("%s", condition),
			tuple([self.doc.delivery_note] + rows), as_dict=1)

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

	def update_item_details(self):
		"""
			Fill empty columns in Packing Slip Item
		"""
		if not self.doc.from_case_no:
			self.doc.from_case_no = self.get_recommended_case_no()

		for d in self.doclist.get({"parentfield": "item_details"}):
			res = webnotes.conn.get_value("Item", d.item_code, 
				["net_weight", "weight_uom"], as_dict=True)
			
			if res and len(res)>0:
				d.net_weight = res["net_weight"]
				d.weight_uom = res["weight_uom"]

	def get_recommended_case_no(self):
		"""
			Returns the next case no. for a new packing slip for a delivery
			note
		"""
		recommended_case_no = webnotes.conn.sql("""SELECT MAX(to_case_no) FROM `tabPacking Slip`
			WHERE delivery_note = %(delivery_note)s AND docstatus=1""", self.doc.fields)
		
		return cint(recommended_case_no[0][0]) + 1
		
	def get_items(self):
		self.doclist = self.doc.clear_table(self.doclist, "item_details", 1)
		
		dn_details = self.get_details_for_packing()[0]
		for item in dn_details:
			if flt(item.qty) > flt(item.packed_qty):
				ch = addchild(self.doc, 'item_details', 'Packing Slip Item', self.doclist)
				ch.item_code = item.item_code
				ch.item_name = item.item_name
				ch.stock_uom = item.stock_uom
				ch.qty = flt(item.qty) - flt(item.packed_qty)
		self.update_item_details()

def item_details(doctype, txt, searchfield, start, page_len, filters):
	from controllers.queries import get_match_cond
	return webnotes.conn.sql("""select name, item_name, description from `tabItem` 
				where name in ( select item_code FROM `tabDelivery Note Item` 
	 						where parent= %s 
	 							and ifnull(qty, 0) > ifnull(packed_qty, 0)) 
	 			and %s like "%s" %s 
	 			limit  %s, %s """ % ("%s", searchfield, "%s", 
	 			get_match_cond(doctype, searchfield), "%s", "%s"), 
	 			(filters["delivery_note"], "%%%s%%" % txt, start, page_len))