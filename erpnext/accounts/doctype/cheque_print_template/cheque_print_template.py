# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt, cstr

class ChequePrintTemplate(Document):
	def on_update(self):
		if not frappe.db.exists("Print Format", self.name):
			cheque_print = frappe.new_doc("Print Format")
			cheque_print.update({
				"doc_type": "Journal Entry",
				"standard": "Yes",
				"custom_format": 1,
				"print_format_type": "Server",
				"name": self.name
			})
		else:
			cheque_print = frappe.get_doc("Print Format", self.name)
		
		
		cheque_print.html = """
<div style="position: relative">
	<div style="width:%scm;height:%scm;">
		<span style="top:%s cm; left:%scm;position: absolute;">
			{{doc.cheque_date or '' }}
		</span>
		<span style="top:%scm;left:%scm;position: absolute;">
			1234567890
		</span>
		<span style="top:%scm;left: %scm; position: absolute;">
			{{doc.pay_to_recd_from}}
		</span>
		<span style="top:%scm; left:%scm; position: absolute; display: block;
			width: %scm; line-height:%scm; word-wrap: break-word;">
				{{doc.total_amount_in_words}}
		</span>
		<span style="top:%scm;left: %scm;position: absolute;">
			{{doc.get_formatted("total_amount")}}
		</span>
		<span style="top:%scm;left: %scm; position: absolute;">
			{{doc.company}}
		</span>
</div>"""%(self.cheque_width, self.cheque_height,
		self.date_dist_from_top_edge, self.date_dist_from_left_edge,
		self.acc_no_dist_from_top_edge, self.acc_no_dist_from_left_edge,
		self.payer_name_from_top_edge, self.payer_name_from_left_edge,
		self.amt_in_words_from_top_edge, self.amt_in_words_from_left_edge,
		self.amt_in_word_width, self.amt_in_words_line_spacing,
		self.amt_in_figures_from_top_edge, self.amt_in_figures_from_left_edge,
		self.signatory_from_top_edge, self.signatory_from_left_edge)
			
		cheque_print.save(ignore_permissions=True)
		
			
