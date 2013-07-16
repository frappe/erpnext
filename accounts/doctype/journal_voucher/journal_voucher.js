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
		cur_frm.add_custom_button('View Ledger', function() {
			wn.route_options = {
				"voucher_no": doc.name,
				"from_date": doc.posting_date,
				"to_date": doc.posting_date,
			};
			wn.set_route("general-ledger");
		});
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

cur_frm.fields_dict['entries'].grid.onrowadd = function(doc, cdt, cdn){
	var d = locals[cdt][cdn];
	if(d.idx == 1){
		d.debit = 0;
		d.credit = 0;
	}
}

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
		td += flt(el[i].debit, 2);
		tc += flt(el[i].credit, 2);
	}
	var doc = locals[doc.doctype][doc.name];
	doc.total_debit = td;
	doc.total_credit = tc;
	doc.difference = flt((td - tc), 2);
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

cur_frm.cscript.voucher_type = function(doc, cdt, cdn) {
	cur_frm.set_df_property("cheque_no", "reqd", doc.voucher_type=="Bank Voucher");
	cur_frm.set_df_property("cheque_date", "reqd", doc.voucher_type=="Bank Voucher");

	if(wn.model.get("Journal Voucher Detail", {"parent":doc.name}).length!==0 // too late
		|| !doc.company) // too early
		return;
	
	var update_jv_details = function(doc, r) {
		$.each(r.message, function(i, d) {
			var jvdetail = wn.model.add_child(doc, "Journal Voucher Detail", "entries");
			jvdetail.account = d.account;
			jvdetail.balance = d.balance;
		});
		refresh_field("entries");
	}
	
	if(in_list(["Bank Voucher", "Cash Voucher"], doc.voucher_type)) {
		wn.call({
			type: "GET",
			method: "accounts.doctype.journal_voucher.journal_voucher.get_default_bank_cash_account",
			args: {
				"voucher_type": doc.voucher_type,
				"company": doc.company
			},
			callback: function(r) {
				if(r.message) {
					update_jv_details(doc, r);
				}
			}
		})
	} else if(doc.voucher_type=="Opening Entry") {
		wn.call({
			type:"GET",
			method: "accounts.doctype.journal_voucher.journal_voucher.get_opening_accounts",
			args: {
				"company": doc.company
			},
			callback: function(r) {
				wn.model.clear_table("Journal Voucher Detail", "Journal Voucher", 
					doc.name, "entries");
				if(r.message) {
					update_jv_details(doc, r);
				}
				cur_frm.set_value("is_opening", "Yes")
			}
		})
	}
}

// get_query

cur_frm.fields_dict['entries'].grid.get_field('account').get_query = function(doc) {
	return {
		filters: { 
			group_or_ledger: "Ledger",
			company: doc.company
		}
	}
}

cur_frm.fields_dict["entries"].grid.get_field("cost_center").get_query = function(doc) {
	return {
		filters: { 
			'company': doc.company,
			'group_or_ledger': 'Ledger'
		}
	}
}

cur_frm.fields_dict['entries'].grid.get_field('against_voucher').get_query = function(doc) {	
	var d = locals[this.doctype][this.docname];
	return {
		filters: [
			['Purchase Invoice', 'credit_to', '=', d.account],
			['Purchase Invoice', 'docstatus', '=', 1],
			['Purchase Invoice', 'outstanding_amount', '>', 0]
		]
	}
}

cur_frm.fields_dict['entries'].grid.get_field('against_invoice').get_query = function(doc) {
	var d = locals[this.doctype][this.docname];
	return {
		filters: [
			['Sales Invoice', 'debit_to', '=', d.account],
			['Sales Invoice', 'docstatus', '=', 1],
			['Sales Invoice', 'outstanding_amount', '>', 0]
		]
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