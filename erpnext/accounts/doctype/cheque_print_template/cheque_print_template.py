# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class ChequePrintTemplate(Document):
	pass

@frappe.whitelist()
def create_or_update_cheque_print_format(template_name):
	if not frappe.db.exists("Print Format", template_name):
		cheque_print = frappe.new_doc("Print Format")
		cheque_print.update({
			"doc_type": "Journal Entry",
			"standard": "No",
			"custom_format": 1,
			"print_format_type": "Server",
			"name": template_name
		})
	else:
		cheque_print = frappe.get_doc("Print Format", template_name)
	
	doc = frappe.get_doc("Cheque Print Template", template_name)
	
	cheque_print.html = """
<div style="position: relative; top:%(starting_position_from_top_edge)scm">
	<div style="width:%(cheque_width)scm;height:%(cheque_height)scm;">
		<span style="top:%(date_dist_from_top_edge)s cm; left:%(date_dist_from_left_edge)scm;
			position: absolute;">
			{{doc.cheque_date or '' }}
		</span>
		<span style="top:%(acc_no_dist_from_top_edge)scm;left:%(acc_no_dist_from_left_edge)scm;
			position: absolute;">
			{{ doc.account_no or "Account No" }}
		</span>
		<span style="top:%(payer_name_from_top_edge)scm;left: %(payer_name_from_left_edge)scm;
			position: absolute;">
			{{doc.pay_to_recd_from}}
		</span>
		<span style="top:%(amt_in_words_from_top_edge)scm; left:%(amt_in_words_from_left_edge)scm;
			position: absolute; display: block; width: %(amt_in_word_width)scm;
			line-height:%(amt_in_words_line_spacing)scm; word-wrap: break-word;">
				{{doc.total_amount_in_words}}
		</span>
		<span style="top:%(amt_in_figures_from_top_edge)scm;left: %(amt_in_figures_from_left_edge)scm;
			position: absolute;">
			{{doc.get_formatted("total_amount")}}
		</span>
		<span style="top:%(signatory_from_top_edge)scm;left: %(signatory_from_left_edge)scm;
			position: absolute;">
			{{doc.company}}
		</span>
	</div>
</div>"""%{
		"starting_position_from_top_edge": doc.starting_position_from_top_edge \
			if doc.cheque_size == "A4" else 0.0,
		"cheque_width": doc.cheque_width, "cheque_height": doc.cheque_height,
		"date_dist_from_top_edge": doc.date_dist_from_top_edge,
		"date_dist_from_left_edge": doc.date_dist_from_left_edge,
		"acc_no_dist_from_top_edge": doc.acc_no_dist_from_top_edge,
		"acc_no_dist_from_left_edge": doc.acc_no_dist_from_left_edge,
		"payer_name_from_top_edge": doc.payer_name_from_top_edge,
		"payer_name_from_left_edge": doc.payer_name_from_left_edge,
		"amt_in_words_from_top_edge": doc.amt_in_words_from_top_edge,
		"amt_in_words_from_left_edge": doc.amt_in_words_from_left_edge,
		"amt_in_word_width": doc.amt_in_word_width,
		"amt_in_words_line_spacing": doc.amt_in_words_line_spacing,
		"amt_in_figures_from_top_edge": doc.amt_in_figures_from_top_edge,
		"amt_in_figures_from_left_edge": doc.amt_in_figures_from_left_edge,
		"signatory_from_top_edge": doc.signatory_from_top_edge,
		"signatory_from_left_edge": doc.signatory_from_left_edge
	}
		
	cheque_print.save(ignore_permissions=True)
	
	frappe.db.set_value("Cheque Print Template", template_name, "has_print_format", 1)
		
	return cheque_print
