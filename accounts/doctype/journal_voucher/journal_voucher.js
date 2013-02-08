// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

cur_frm.cscript.onload = function(doc, cdt, cdn) {
	cur_frm.cscript.load_defaults(doc, cdt, cdn);
}

cur_frm.cscript.refresh = function(doc) {
	cur_frm.cscript.is_opening(doc)
	erpnext.hide_naming_series();
	cur_frm.cscript.voucher_type(doc);
	if(doc.docstatus==1) { 
		cur_frm.add_custom_button('View Ledger', cur_frm.cscript.view_ledger_entry);
	}
}

cur_frm.cscript.load_defaults = function(doc, cdt, cdn) {
	if(!cur_frm.doc.__islocal || !cur_frm.doc.company) { return; }

	doc = locals[doc.doctype][doc.name];
	var fields_to_refresh = wn.model.set_default_values(doc);
	if(fields_to_refresh) { refresh_many(fields_to_refresh); }

	fields_to_refresh = null;
	var children = getchildren('Journal Voucher Detail', doc.name, 'entries');
	if(!children) { return; }
	for(var i=0; i<children.length; i++) {
		wn.model.set_default_values(children[i]);
	}
	refresh_field('entries');
}


cur_frm.cscript.is_opening = function(doc, cdt, cdn) {
	hide_field('aging_date');
	if (doc.is_opening == 'Yes') unhide_field('aging_date');
}

//Set debit and credit to zero on adding new row
//----------------------------------------------
cur_frm.fields_dict['entries'].grid.onrowadd = function(doc, cdt, cdn){
	var d = locals[cdt][cdn];
	if(d.idx == 1){
		d.debit = 0;
		d.credit = 0;
	}
}

// Get Outstanding of Payable & Sales Invoice
// -----------------------------------------------

cur_frm.cscript.against_voucher = function(doc,cdt,cdn) {
	var d = locals[cdt][cdn];
	if (d.against_voucher && !flt(d.debit)) {
		args = {'doctype': 'Purchase Invoice', 'docname': d.against_voucher }
		get_server_fields('get_outstanding',docstring(args),'entries',doc,cdt,cdn,1,function(r,rt) { cur_frm.cscript.update_totals(doc); });
	}
}

cur_frm.cscript.against_invoice = function(doc,cdt,cdn) {
	var d = locals[cdt][cdn];
	if (d.against_invoice && !flt(d.credit)) {
		args = {'doctype': 'Sales Invoice', 'docname': d.against_invoice }
		get_server_fields('get_outstanding',docstring(args),'entries',doc,cdt,cdn,1,function(r,rt) { cur_frm.cscript.update_totals(doc); });
	}
}

// Update Totals

cur_frm.cscript.update_totals = function(doc) {
	var td=0.0; var tc =0.0;
	var el = getchildren('Journal Voucher Detail', doc.name, 'entries');
	for(var i in el) {
		td += flt(el[i].debit);
		tc += flt(el[i].credit);
	}
	var doc = locals[doc.doctype][doc.name];
	doc.total_debit = td;
	doc.total_credit = tc;
	doc.difference = flt(td - tc);
	refresh_many(['total_debit','total_credit','difference']);
}

cur_frm.cscript.debit = function(doc,dt,dn) { cur_frm.cscript.update_totals(doc); }
cur_frm.cscript.credit = function(doc,dt,dn) { cur_frm.cscript.update_totals(doc); }

cur_frm.cscript.get_balance = function(doc,dt,dn) {
	cur_frm.cscript.update_totals(doc); 
	$c_obj(make_doclist(dt,dn), 'get_balance', '', function(r, rt){
	cur_frm.refresh();
	});
}
// Get balance
// -----------

cur_frm.cscript.account = function(doc,dt,dn) {
	var d = locals[dt][dn];
	wn.call({
		method: "accounts.utils.get_balance_on",
		args: {account: d.account, date: doc.posting_date},
		callback: function(r) {
			d.balance = format_currency(r.message, erpnext.get_currency(doc.company));
			refresh_field('balance', d.name, 'entries');
		}
	});
} 

cur_frm.cscript.validate = function(doc,cdt,cdn) {
	cur_frm.cscript.update_totals(doc);
}

cur_frm.cscript.select_print_heading = function(doc,cdt,cdn){
	if(doc.select_print_heading){
		// print heading
		cur_frm.pformat.print_heading = doc.select_print_heading;
	}
	else
		cur_frm.pformat.print_heading = "Journal Voucher";
}

cur_frm.cscript.view_ledger_entry = function(doc,cdt,cdn){
	wn.set_route('Report', 'GL Entry', 'General Ledger', 'Voucher No='+cur_frm.doc.name);	
}


cur_frm.cscript.voucher_type = function(doc, cdt, cdn) {
	if(doc.voucher_type == 'Bank Voucher' && cstr(doc.company)) {
		cur_frm.set_df_property("cheque_no", "reqd", true);
		cur_frm.set_df_property("cheque_date", "reqd", true);

		var children = getchildren('Journal Voucher Detail', doc.name, 'entries');
		if(!children || children.length==0) {
			$c('accounts.get_default_bank_account', {company: doc.company }, function(r, rt) {
				if(!r.exc) {
					var jvd = wn.model.add_child(doc, 'Journal Voucher Detail', 'entries');
					jvd.account = cstr(r.message);
					refresh_field('entries');
				}
			});
		}
	} else {
		cur_frm.set_df_property("cheque_no", "reqd", false);
		cur_frm.set_df_property("cheque_date", "reqd", false);		
	}
}

// get_query

cur_frm.fields_dict['entries'].grid.get_field('account').get_query = function(doc) {
	return {
		query: "accounts.utils.get_account_list",
		filters: { company: doc.company	}
	}
}

cur_frm.fields_dict["entries"].grid.get_field("cost_center").get_query = function(doc) {
	return {
		query: "accounts.utils.get_cost_center_list",
		filters: { company_name: doc.company}
	}
}

cur_frm.fields_dict['entries'].grid.get_field('against_voucher').get_query = function(doc) {	
	var d = locals[this.doctype][this.docname];
	return {
		query: "accounts.doctype.journal_voucher.journal_voucher.get_against_purchase_invoice",
		filters: { account: d.account }
	}
}

cur_frm.fields_dict['entries'].grid.get_field('against_invoice').get_query = function(doc) {
	var d = locals[this.doctype][this.docname];
	return {
		query: "accounts.doctype.journal_voucher.journal_voucher.get_against_sales_invoice",
		filters: { account: d.account }
	}
}

cur_frm.fields_dict['entries'].grid.get_field('against_jv').get_query = function(doc) {
	var d = locals[this.doctype][this.docname];
	
	if(!d.account) {
		msgprint("Please select Account first!")
		throw "account not selected"
	}
	
	return {
		query: "accounts.doctype.journal_voucher.journal_voucher.get_against_jv",
		filters: { account: d.account }
	}
}