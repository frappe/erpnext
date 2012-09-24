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
	if (!doc.voucher_date) doc.voucher_date = dateutil.obj_to_str(new Date());

	var cp = wn.control_panel;
	if(cp.country == 'India') $(cur_frm.fields_dict.tds.row.wrapper).toggle(true);
	else $(cur_frm.fields_dict.tds.row.wrapper).toggle(false);

	cur_frm.cscript.load_defaults(doc, cdt, cdn);
}

cur_frm.cscript.refresh = function(doc) {
	cur_frm.cscript.is_opening(doc)
	erpnext.hide_naming_series();
}

cur_frm.cscript.load_defaults = function(doc, cdt, cdn) {
	if(!cur_frm.doc.__islocal || !cur_frm.doc.company) { return; }

	doc = locals[doc.doctype][doc.name];
	var fields_to_refresh = LocalDB.set_default_values(doc);
	if(fields_to_refresh) { refresh_many(fields_to_refresh); }

	fields_to_refresh = null;
	var children = getchildren('Journal Voucher Detail', doc.name, 'entries');
	if(!children) { return; }
	for(var i=0; i<children.length; i++) {
		LocalDB.set_default_values(children[i]);
	}
	refresh_field('entries');
}


cur_frm.cscript.is_opening = function(doc, cdt, cdn) {
	hide_field('aging_date');
	if (doc.is_opening == 'Yes') unhide_field('aging_date');
	
	if(doc.docstatus==1) { unhide_field('view_ledger_entry'); }
	else hide_field('view_ledger_entry');
}

cur_frm.fields_dict['entries'].grid.get_field('account').get_query = function(doc) {
	return "SELECT `tabAccount`.name FROM `tabAccount` WHERE `tabAccount`.company='"+doc.company+"' AND tabAccount.group_or_ledger = 'Ledger' AND tabAccount.docstatus != 2 AND `tabAccount`.%(key)s LIKE '%s' ORDER BY `tabAccount`.name DESC LIMIT 50";
}

cur_frm.fields_dict["entries"].grid.get_field("cost_center").get_query = function(doc, cdt, cdn) {
	return 'SELECT `tabCost Center`.`name` FROM `tabCost Center` WHERE `tabCost Center`.`company_name` = "' +doc.company+'" AND `tabCost Center`.%(key)s LIKE "%s" AND `tabCost Center`.`group_or_ledger` = "Ledger" AND `tabCost Center`.docstatus != 2 ORDER BY	`tabCost Center`.`name` ASC LIMIT 50';
}

// Restrict Voucher based on Account
// ---------------------------------
cur_frm.fields_dict['entries'].grid.get_field('against_voucher').get_query = function(doc) {
	var d = locals[this.doctype][this.docname];
	return "SELECT `tabPurchase Invoice`.name, `tabPurchase Invoice`.credit_to, `tabPurchase Invoice`.outstanding_amount,`tabPurchase Invoice`.bill_no, `tabPurchase Invoice`.bill_date FROM `tabPurchase Invoice` WHERE `tabPurchase Invoice`.credit_to='"+d.account+"' AND `tabPurchase Invoice`.outstanding_amount > 0 AND `tabPurchase Invoice`.docstatus = 1 AND `tabPurchase Invoice`.%(key)s LIKE '%s' ORDER BY `tabPurchase Invoice`.name DESC LIMIT 200";
}

cur_frm.fields_dict['entries'].grid.get_field('against_invoice').get_query = function(doc) {
	var d = locals[this.doctype][this.docname];
	return "SELECT `tabSales Invoice`.name, `tabSales Invoice`.debit_to, `tabSales Invoice`.outstanding_amount FROM `tabSales Invoice` WHERE `tabSales Invoice`.debit_to='"+d.account+"' AND `tabSales Invoice`.outstanding_amount > 0 AND `tabSales Invoice`.docstatus = 1 AND `tabSales Invoice`.%(key)s LIKE '%s' ORDER BY `tabSales Invoice`.name DESC LIMIT 200";
}

// TDS Account Head
cur_frm.fields_dict['tax_code'].get_query = function(doc) {
	return "SELECT `tabTDS Category Account`.account_head FROM `tabTDS Category Account` WHERE `tabTDS Category Account`.parent = '"+doc.tds_category+"' AND `tabTDS Category Account`.company='"+doc.company+"' AND `tabTDS Category Account`.account_head LIKE '%s' ORDER BY `tabTDS Category Account`.account_head DESC LIMIT 50";
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
// ---------------
cur_frm.cscript.update_totals = function(doc) {
	var td=0.0; var tc =0.0;
	var el = getchildren('Journal Voucher Detail', doc.name, 'entries');
	for(var i in el) {
		td += flt(el[i].debit);
		tc += flt(el[i].credit);
	}
	var doc = locals[doc.doctype][doc.name];
	tc += flt(doc.ded_amount)
	doc.total_debit = td;
	doc.total_credit = tc;
	doc.difference = flt(td - tc);
	refresh_many(['total_debit','total_credit','difference']);
}

cur_frm.cscript.debit = function(doc,dt,dn) { cur_frm.cscript.update_totals(doc); }
cur_frm.cscript.credit = function(doc,dt,dn) { cur_frm.cscript.update_totals(doc); }
cur_frm.cscript.ded_amount = function(doc,dt,dn) { cur_frm.cscript.update_totals(doc); }
cur_frm.cscript.rate = function(doc,dt,dn) {
	doc.ded_amount = doc.total_debit*doc.rate/100;
	refresh_field('ded_amount');
	cur_frm.cscript.update_totals(doc); 
}
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
	$c_obj('GL Control','get_bal',d.account+'~~~'+doc.fiscal_year, function(r,rt) { d.balance = r.message; refresh_field('balance',d.name,'entries'); });
} 

cur_frm.cscript.validate = function(doc,cdt,cdn) {
	cur_frm.cscript.update_totals(doc);
}

// TDS
// --------
cur_frm.cscript.get_tds = function(doc, dt, dn) {
	$c_obj(make_doclist(dt,dn), 'get_tds', '', function(r, rt){
		cur_frm.refresh();
		cur_frm.cscript.update_totals(doc);
	});
}

// ***************** Get Print Heading based on Sales Invoice *****************
cur_frm.fields_dict['select_print_heading'].get_query = function(doc, cdt, cdn) {
	return 'SELECT `tabPrint Heading`.name FROM `tabPrint Heading` WHERE `tabPrint Heading`.docstatus !=2 AND `tabPrint Heading`.name LIKE "%s" ORDER BY `tabPrint Heading`.name ASC LIMIT 50';
}



cur_frm.cscript.select_print_heading = function(doc,cdt,cdn){
	if(doc.select_print_heading){
		// print heading
		cur_frm.pformat.print_heading = doc.select_print_heading;
	}
	else
		cur_frm.pformat.print_heading = "Journal Voucher";
}

/****************** Get Accounting Entry *****************/
cur_frm.cscript.view_ledger_entry = function(doc,cdt,cdn){
	wn.set_route('Report', 'GL Entry', 'General Ledger', 'Voucher No='+cur_frm.doc.name);	
}


cur_frm.cscript.voucher_type = function(doc, cdt, cdn) {
	if(doc.voucher_type == 'Bank Voucher' && cstr(doc.company)) {
		var children = getchildren('Journal Voucher Detail', doc.name, 'entries');
		if(!children || children.length==0) {
			$c('accounts.get_default_bank_account', {company: doc.company }, function(r, rt) {
				if(!r.exc) {
					var jvd = LocalDB.add_child(doc, 'Journal Voucher Detail', 'entries');
					jvd.account = cstr(r.message);
					refresh_field('entries');
				}
			});
		}
	}
}
