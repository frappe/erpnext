// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

{% include "public/js/controllers/accounts.js" %}

cur_frm.cscript.onload = function(doc, cdt, cdn) {
	if(doc.doctype === "Sales Taxes and Charges Master")
		erpnext.add_applicable_territory();
}

cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	cur_frm.set_footnote(frappe.markdown(cur_frm.meta.description));
}

// For customizing print
cur_frm.pformat.net_total_export = function(doc) {
	return '';
}

cur_frm.pformat.discount_amount = function(doc) {
	return '';
}

cur_frm.pformat.grand_total_export = function(doc) {
	return '';
}

cur_frm.pformat.rounded_total_export = function(doc) {
	return '';
}

cur_frm.pformat.in_words_export = function(doc) {
	return '';
}

cur_frm.pformat.other_charges= function(doc){
	//function to make row of table
	var make_row = function(title, val, bold){
		var bstart = '<b>'; var bend = '</b>';
		return '<tr><td style="width:50%;">' + (bold?bstart:'') + title + (bold?bend:'') + '</td>'
			+ '<td style="width:50%;text-align:right;">' + format_currency(val, doc.currency) + '</td>'
			+ '</tr>';
	}

	function convert_rate(val) {
		var new_val = flt(val)/flt(doc.conversion_rate);
		return new_val;
	}
	
	function print_hide(fieldname) {
		var doc_field = frappe.meta.get_docfield(doc.doctype, fieldname, doc.name);
		return doc_field.print_hide;
	}
	
	out ='';
	if (!doc.print_without_amount) {
		var cl = doc.other_charges || [];

		// outer table	
		var out='<div><table class="noborder" style="width:100%"><tr><td style="width: 60%"></td><td>';

		// main table

		out +='<table class="noborder" style="width:100%">';

		if(!print_hide('net_total_export')) {
			out += make_row('Net Total', doc.net_total_export, 1);
		}

		// add rows
		if(cl.length){
			for(var i=0;i<cl.length;i++) {
				if(convert_rate(cl[i].tax_amount)!=0 && !cl[i].included_in_print_rate)
					out += make_row(cl[i].description, convert_rate(cl[i].tax_amount), 0);
			}
		}

		// Discount Amount
		if(!print_hide('discount_amount') && doc.discount_amount)
			out += make_row('Discount Amount', convert_rate(doc.discount_amount), 0);

		// grand total
		if(!print_hide('grand_total_export'))
			out += make_row('Grand Total', doc.grand_total_export, 1);
		
		if(!print_hide('rounded_total_export'))
			out += make_row('Rounded Total', doc.rounded_total_export, 1);

		if(doc.in_words_export && !print_hide('in_words_export')) {
			out +='</table></td></tr>';
			out += '<tr><td colspan = "2">';
			out += '<table><tr><td style="width:25%;"><b>In Words</b></td>';
			out += '<td style="width:50%;">' + doc.in_words_export + '</td></tr>';
		}
		out += '</table></td></tr></table></div>';	 
	}
	return out;
}

cur_frm.cscript.charge_type = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	if(d.idx == 1 && (d.charge_type == 'On Previous Row Amount' || d.charge_type == 'On Previous Row Total')) {
		msgprint(__("Cannot select charge type as 'On Previous Row Amount' or 'On Previous Row Total' for first row"));
		d.charge_type = '';
	}
	validated = false;
	refresh_field('charge_type', d.name, 'other_charges');
	cur_frm.cscript.row_id(doc, cdt, cdn);
	cur_frm.cscript.rate(doc, cdt, cdn);
	cur_frm.cscript.tax_amount(doc, cdt, cdn);
}

cur_frm.cscript.row_id = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	if(!d.charge_type && d.row_id) {
		msgprint(__("Please select Charge Type first"));
		d.row_id = '';
	}
	else if((d.charge_type == 'Actual' || d.charge_type == 'On Net Total') && d.row_id) {
		msgprint(__("Can refer row only if the charge type is 'On Previous Row Amount' or 'Previous Row Total'"));
		d.row_id = '';
	}
	else if((d.charge_type == 'On Previous Row Amount' || d.charge_type == 'On Previous Row Total') && d.row_id) {
		if(d.row_id >= d.idx){
			msgprint(__("Cannot refer row number greater than or equal to current row number for this Charge type"));
			d.row_id = '';
		}
	}
	validated = false;
	refresh_field('row_id', d.name, 'other_charges');
}

/*---------------------- Get rate if account_head has account_type as TAX or CHARGEABLE-------------------------------------*/

cur_frm.fields_dict['other_charges'].grid.get_field("account_head").get_query = function(doc,cdt,cdn) {
	return{
		query: "erpnext.controllers.queries.tax_account_query",
    	filters: {
			"account_type": ["Tax", "Chargeable", "Income Account"],
			"company": doc.company
		}
	}	
}

cur_frm.fields_dict['other_charges'].grid.get_field("cost_center").get_query = function(doc) {
	return{
		'company': doc.company,
		'group_or_ledger': "Ledger"
	}	
}

cur_frm.cscript.rate = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	if(!d.charge_type && d.rate) {
		msgprint(__("Please select Charge Type first"));
		d.rate = '';
	}
	validated = false;
	refresh_field('rate', d.name, 'other_charges');
}

cur_frm.cscript.tax_amount = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	if(!d.charge_type && d.tax_amount) {
		msgprint(__("Please select Charge Type first"));
		d.tax_amount = '';
	}
	else if(d.charge_type && d.tax_amount) {
		msgprint(__("Cannot directly set amount. For 'Actual' charge type, use the rate field"));
		d.tax_amount = '';
	}
	validated = false;
	refresh_field('tax_amount', d.name, 'other_charges');
};
