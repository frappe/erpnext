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

// Preset
// ------
// cur_frm.cscript.tname - Details table name
// cur_frm.cscript.fname - Details fieldname
var tname = cur_frm.cscript.tname;
var fname = cur_frm.cscript.fname;


cur_frm.cscript.get_default_schedule_date = function(doc) {
		var ch = getchildren( tname, doc.name, fname);
		if (flt(ch.length) > 0){
			$c_obj(make_doclist(doc.doctype, doc.name), 'get_default_schedule_date', '', function(r, rt) { refresh_field(fname); });
		}
}


// Gets called after existing item details are update to fill in
// remaining default values
cur_frm.cscript.load_defaults = function(doc, dt, dn) {
	if(!cur_frm.doc.__islocal) { return; }

	doc = locals[doc.doctype][doc.name];
	var fields_to_refresh = LocalDB.set_default_values(doc);
	if(fields_to_refresh) { refresh_many(fields_to_refresh); }

	fields_to_refresh = null;
	var children = getchildren(cur_frm.cscript.tname, doc.name, cur_frm.cscript.fname);
	if(!children) { return; }
	for(var i=0; i<children.length; i++) {
		LocalDB.set_default_values(children[i]);
	}
	refresh_field(cur_frm.cscript.fname);
}

// Update existing item details
cur_frm.cscript.update_item_details = function(doc, dt, dn, callback) {
	if(!cur_frm.doc.__islocal) { return; }
	var children = getchildren(cur_frm.cscript.tname, doc.name, cur_frm.cscript.fname);
	if(children) {
		$c_obj(make_doclist(doc.doctype, doc.name), 'get_item_details', '',
		function(r, rt) {
			if(!r.exc) {
				refresh_field(cur_frm.cscript.fname);
				doc = locals[doc.doctype][doc.name];
				cur_frm.cscript.load_defaults(doc, dt, dn);
				if(callback) callback(doc, dt, dn);
			}
		});
	}
}

var set_dynamic_label_par = function(doc, cdt, cdn, base_curr) {
	//parent flds
	par_cols_base = {'net_total': 'Net Total', 'total_tax': 'Total Tax', 'grand_total':	'Grand Total', /*'rounded_total': 'Rounded Total',*/
		'in_words': 'In Words', 'other_charges_added': 'Taxes and Charges Added', 'other_charges_deducted': 'Taxes and Charges Deducted'}
	par_cols_import = {'net_total_import': 'Net Total', 'grand_total_import': 'Grand Total', 'in_words_import':	'In Words', 
		'other_charges_added_import': 'Taxes and Charges Added', 'other_charges_deducted_import': 'Taxes and Charges Deducted'};

	for (d in par_cols_base) cur_frm.fields_dict[d].label_area.innerHTML = par_cols_base[d]+' (' + base_curr + ')';
	for (d in par_cols_import) cur_frm.fields_dict[d].label_area.innerHTML = par_cols_import[d]+' (' + doc.currency + ')';
	cur_frm.fields_dict['conversion_rate'].label_area.innerHTML = "Conversion Rate (" + doc.currency +' -> '+ base_curr + ')';

	if (doc.doctype == 'Purchase Invoice') {
		cur_frm.fields_dict['total_tds_on_voucher'].label_area.innerHTML = 'Total TDS On Voucher (' + base_curr + ')';
		cur_frm.fields_dict['outstanding_amount'].label_area.innerHTML = 'Outstanding Amount (' + base_curr + ')';
		cur_frm.fields_dict['tds_amount_on_advance'].label_area.innerHTML = 'TDS Amount On Advance (' + base_curr + ')';
		cur_frm.fields_dict['total_advance'].label_area.innerHTML = 'Total Advance (Incl. TDS) (' + base_curr + ')';
		cur_frm.fields_dict['total_amount_to_pay'].label_area.innerHTML = 'Total Amount To Pay (' + base_curr + ')';
		cur_frm.fields_dict['ded_amount'].label_area.innerHTML = 'TDS Amount (' + base_curr + ')';
	} else cur_frm.fields_dict['rounded_total'].label_area.innerHTML = 'Rounded Total (' + base_curr + ')';

}


var set_dynamic_label_child = function(doc, cdt, cdn, base_curr) {
	// item table flds
	item_cols_base = {'purchase_ref_rate': 'Ref Rate', 'amount': 'Amount'};
	item_cols_import = {'import_rate': 'Rate', 'import_ref_rate': 'Ref Rate', 'import_amount': 'Amount'};
		
	for (d in item_cols_base) $('[data-grid-fieldname="'+cur_frm.cscript.tname+'-'+d+'"]').html(item_cols_base[d]+' ('+base_curr+')');
	for (d in item_cols_import) $('[data-grid-fieldname="'+cur_frm.cscript.tname+'-'+d+'"]').html(item_cols_import[d]+' ('+doc.currency+')');
		
	var hide = (doc.currency == sys_defaults['currency']) ? false : true;
	for (f in item_cols_base) {
		cur_frm.fields_dict[cur_frm.cscript.fname].grid.set_column_disp(f, hide);
	}
	if (doc.doctype == 'Purchase Invoice') {
		$('[data-grid-fieldname="'+cur_frm.cscript.tname+'-rate"]').html('Rate ('+base_curr+')');
		cur_frm.fields_dict[cur_frm.cscript.fname].grid.set_column_disp('rate', hide);
		// advance table flds
		adv_cols = {'advance_amount': 'Advance Amount', 'allocated_amount': 'Allocated Amount', 'tds_amount': 'TDS Amount', 'tds_allocated': 'TDS Allocated'}
		for (d in adv_cols) $('[data-grid-fieldname="Purchase Invoice Advance-'+d+'"]').html(adv_cols[d]+' ('+base_curr+')');	
	}
	else {
		$('[data-grid-fieldname="'+cur_frm.cscript.tname+'-purchase_rate"]').html('Rate ('+base_curr+')');
		cur_frm.fields_dict[cur_frm.cscript.fname].grid.set_column_disp('purchase_rate', hide);
	}

	//tax table flds
	tax_cols = {'tax_amount': 'Amount', 'total': 'Aggregate Total'};
	for (d in tax_cols) $('[data-grid-fieldname="Purchase Taxes and Charges-'+d+'"]').html(tax_cols[d]+' ('+base_curr+')');	
}

// Change label dynamically based on currency
//------------------------------------------------------------------

cur_frm.cscript.dynamic_label = function(doc, cdt, cdn, callback1) {
	var base_currency = wn.boot.company[doc.company].default_currency || sys_defaults['currency'];
	if (doc.currency === base_currency) {
		set_multiple(cdt, cdn, {conversion_rate:1});
		hide_field(['conversion_rate', 'net_total_import','grand_total_import',
			'in_words_import', 'other_charges_added_import', 'other_charges_deducted_import']);
	} else {
		unhide_field(['conversion_rate', 'net_total_import','grand_total_import',
			'in_words_import', 'other_charges_added_import', 'other_charges_deducted_import']);
	}
	
	set_dynamic_label_par(doc, cdt, cdn, base_currency);
	set_dynamic_label_child(doc, cdt, cdn, base_currency);
	
	if (callback1) callback1(doc, cdt, cdn);
}

cur_frm.cscript.currency = function(doc, cdt, cdn) {
	cur_frm.cscript.dynamic_label(doc, cdt, cdn);
}

cur_frm.cscript.company = cur_frm.cscript.currency;


// ======================== Conversion Rate ==========================================
cur_frm.cscript.conversion_rate = function(doc,cdt,cdn) {
	cur_frm.cscript.calc_amount( doc, 1);
}

//==================== Item Code Get Query =======================================================
// Only Is Purchase Item = 'Yes' and Items not moved to trash are allowed.
cur_frm.fields_dict[fname].grid.get_field("item_code").get_query = function(doc, cdt, cdn) {
	if (doc.is_subcontracted =="Yes") {
		return 'SELECT tabItem.name, tabItem.description FROM tabItem WHERE ifnull(tabItem.is_sub_contracted_item, "No")="Yes" AND (IFNULL(`tabItem`.`end_of_life`,"") = "" OR `tabItem`.`end_of_life` ="0000-00-00" OR `tabItem`.`end_of_life` > NOW()) AND tabItem.docstatus != 2 AND tabItem.%(key)s LIKE "%s" LIMIT 50'
	} else {
		return 'SELECT tabItem.name, tabItem.description FROM tabItem WHERE ifnull(tabItem.is_purchase_item, "No")="Yes" AND (IFNULL(`tabItem`.`end_of_life`,"") = "" OR `tabItem`.`end_of_life` ="0000-00-00" OR `tabItem`.`end_of_life` > NOW()) AND tabItem.docstatus != 2 AND tabItem.%(key)s LIKE "%s" LIMIT 50'
	}
}

//==================== Get Item Code Details =====================================================
cur_frm.cscript.item_code = function(doc,cdt,cdn) {
	var d = locals[cdt][cdn];
	if (d.item_code) {
		temp = {
			item_code: d.item_code || '',
			warehouse: d.warehouse || ''
		}
		get_server_fields('get_item_details', JSON.stringify(temp), fname, doc, cdt, cdn, 1);
	}
}

//==================== Update Stock Qty ==========================================================
cur_frm.cscript.update_stock_qty = function(doc,cdt,cdn){
	d = locals[cdt][cdn]
	// Step 1:=> Check if qty , uom, conversion_factor
	if (d.qty && d.uom && d.conversion_factor){
		// Step 2:=> Set stock_qty = qty * conversion_factor
		d.stock_qty = flt(flt(d.qty) * flt(d.conversion_factor));
		// Step 3:=> Refer stock_qty field a that particular row.
		refresh_field('stock_qty' , d.name,fname);
	}
}

//==================== UOM ======================================================================
cur_frm.cscript.uom = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	if (d.item_code && d.uom) {
		call_back = function(doc, cdt, cdn){
			cur_frm.cscript.calc_amount(doc, 2);
		}
		str_arg = {'item_code':d.item_code, 'uom':d.uom, 'stock_qty':flt(d.stock_qty), 'qty': flt(d.qty), 'conversion_rate':doc.conversion_rate, 'doc_name': doc.name}
		// Updates Conversion Factor, Qty and Purchase Rate
		get_server_fields('get_uom_details',JSON.stringify(str_arg), fname, doc,cdt,cdn,1, call_back);
		// don't make mistake of calling update_stock_qty() the get_uom_details returns stock_qty as per conversion factor properly
	}
}


//==================== Conversion factor =========================================================
cur_frm.cscript.conversion_factor = function(doc, cdt, cdn) {
	cur_frm.cscript.uom(doc, cdt, cdn);
}

//==================== stock qty ======================================================================
cur_frm.cscript.stock_qty = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	if(d.uom && d.qty){
		d.conversion_factor = flt(d.stock_qty)/flt(d.qty);
		refresh_field('conversion_factor', d.name, fname);
	}
}

//==================== Warehouse ================================================================
cur_frm.cscript.warehouse = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	if (d.item_code && d.warehouse) {
		str_arg = "{'item_code':'" +	(d.item_code?d.item_code:'') + "', 'warehouse':'" + (d.warehouse?d.warehouse:'') + "'}"
		get_server_fields('get_bin_details', str_arg, fname, doc, cdt, cdn, 1);
	}	
}

//=================== Quantity ===================================================================
cur_frm.cscript.qty = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	// Step 1: => Update Stock Qty 
	cur_frm.cscript.update_stock_qty(doc,cdt,cdn);
	// Step 2: => Calculate Amount
	cur_frm.cscript.calc_amount(doc, 2);
}


//=================== Purchase Rate ==============================================================
cur_frm.cscript.purchase_rate = function(doc, cdt, cdn) {
	cur_frm.cscript.calc_amount(doc, 2);
}

//==================== Import Rate ================================================================
cur_frm.cscript.import_rate = function(doc, cdt, cdn) {
	cur_frm.cscript.calc_amount(doc, 1);
}

//==================== Discount Rate ================================================================
cur_frm.cscript.discount_rate = function(doc, cdt, cdn) {
	cur_frm.cscript.calc_amount(doc, 4);
}
//==================== Purchase Ref Rate ================================================================
cur_frm.cscript.purchase_ref_rate = function(doc, cdt, cdn) {
	cur_frm.cscript.calc_amount(doc, 4);
}
//==================== Import Ref Rate ================================================================
cur_frm.cscript.import_ref_rate = function(doc, cdt, cdn) {
	cur_frm.cscript.calc_amount(doc, 5);
}

//==================== check if item table is blank ==============================================
var is_item_table = function(doc,cdt,cdn) {
	// Step 1 :=>Get all childrens/ rows from Detail Table
	var cl = getchildren(tname, doc.name, fname);
	// Step 2 :=> If there are no rows then set validated = false, this will stop further execution of code.
	if (cl.length == 0) {
		alert("There is no item in table"); validated = false;
	}
}

//==================== Validate ====================================================================
cur_frm.cscript.validate = function(doc, cdt, cdn) {
	// Step 1:=> check if item table is blank
	is_item_table(doc,cdt,cdn);
	// Step 2:=> Calculate Amount
	cur_frm.cscript.calc_amount(doc, 1);

	// calculate advances if pv
	if(doc.doctype == 'Purchase Invoice') calc_total_advance(doc, cdt, cdn);
}

// **************** RE-CALCULATE VALUES ***************************

cur_frm.cscript.recalculate_values = function(doc, cdt, cdn) {
	cur_frm.cscript.calculate_tax(doc,cdt,cdn);
}

cur_frm.cscript.calculate_tax = function(doc, cdt, cdn) {
	var other_fname	= cur_frm.cscript.other_fname;

	var cl = getchildren('Purchase Taxes and Charges', doc.name, other_fname, doc.doctype);
	for(var i = 0; i<cl.length; i++){
		cl[i].total_tax_amount = 0;
		cl[i].total_amount = 0;
		cl[i].tax_amount = 0;										// this is done to calculate other charges
		cl[i].total = 0;
		if(in_list(['On Previous Row Amount','On Previous Row Total'],cl[i].charge_type) && !cl[i].row_id){
			alert("Please Enter Row on which amount needs to be calculated for row : "+cl[i].idx);
			validated = false;
		}
	}
	cur_frm.cscript.calc_amount(doc, 1);
}



cur_frm.cscript.get_item_wise_tax_detail = function( doc, rate, cl, i, tax, t) {
	doc = locals[doc.doctype][doc.name];
	var detail = '';
	detail = cl[i].item_code + " : " + cstr(rate) + NEWLINE;
	return detail;
}

cur_frm.cscript.amount = function(doc, cdt, cdn) {
	cur_frm.cscript.calc_amount(doc, 3);
}


//====================== Calculate Amount for PO and PR not for PV	============================================================
cur_frm.cscript.calc_amount = function(doc, n) {
	// Set defaults
	doc = locals[doc.doctype][doc.name]
	var other_fname	= cur_frm.cscript.other_fname;
	if(!flt(doc.conversion_rate)) { doc.conversion_rate = 1; refresh_field('conversion_rate'); }
	if(!n) n=0;
	var net_total = 0;
	var net_total_import = 0;
	
	var cl = getchildren(tname, doc.name, fname);
	
	for(var i=0;i<cl.length;i++) 
	{
	var rate_fld = (doc.doctype != 'Purchase Invoice') ? 'purchase_rate': 'rate';
		var tmp = {};
	if(!cl[i].discount_rate) cl[i].discount_rate = 0;

		if(n == 1){ 
			set_multiple(tname, cl[i].name, {'purchase_ref_rate':flt(cl[i].import_ref_rate)*flt(doc.conversion_rate)}, fname);
		set_multiple(tname, cl[i].name, {'discount_rate': flt(flt( flt( flt(cl[i].import_ref_rate) - flt(cl[i].import_rate) ) * 100 )/flt(cl[i].import_ref_rate)) }, fname);
		tmp[rate_fld] = flt(doc.conversion_rate) * flt(cl[i].import_rate);
			set_multiple(tname, cl[i].name, tmp, fname);

			set_multiple(tname, cl[i].name, {'amount': flt(flt(cl[i].qty) * flt(doc.conversion_rate) * flt(cl[i].import_rate))}, fname);
			set_multiple(tname, cl[i].name, {'import_amount': flt(flt(cl[i].qty) * flt(cl[i].import_rate))}, fname);

		}else if(n == 2){
		set_multiple(tname, cl[i].name, {'purchase_ref_rate':flt(cl[i].import_ref_rate)*flt(doc.conversion_rate)}, fname);
		set_multiple(tname, cl[i].name, {'discount_rate': flt(flt( flt( flt(cl[i].purchase_ref_rate) - flt(cl[i][rate_fld]) ) * 100 )/flt(cl[i].purchase_ref_rate)) }, fname);
			set_multiple(tname, cl[i].name, {'amount': flt(flt(cl[i].qty) * flt(cl[i][rate_fld])),}, fname);
		set_multiple(tname, cl[i].name, {'import_rate': flt(flt(cl[i][rate_fld]) / flt(doc.conversion_rate)) }, fname);
			set_multiple(tname, cl[i].name, {'import_amount': flt(flt(cl[i].qty) *	flt(cl[i][rate_fld]) / flt(doc.conversion_rate))}, fname);

	}else if(n == 3){
		tmp[rate_fld] = flt(flt(cl[i].amount) / flt(cl[i].qty));
			set_multiple(tname, cl[i].name, tmp, fname);
			set_multiple(tname, cl[i].name, {'import_rate': flt(flt(cl[i][rate_fld]) / flt(doc.conversion_rate))}, fname); 
			set_multiple(tname, cl[i].name, {'import_amount': flt(flt(cl[i].qty) *	flt(cl[i][rate_fld]) / flt(doc.conversion_rate))}, fname);

		}else if( n==4){

		set_multiple(tname, cl[i].name, {'import_ref_rate': flt(flt(cl[i].purchase_ref_rate) / flt(doc.conversion_rate))}, fname);

			tmp[rate_fld] = flt( flt(cl[i].purchase_ref_rate) - flt(flt(cl[i].purchase_ref_rate)*flt(cl[i].discount_rate)/100) )
		set_multiple(tname, cl[i].name, tmp, fname);
		set_multiple(tname, cl[i].name, {'import_rate': flt(flt(cl[i][rate_fld]) / flt(doc.conversion_rate))}, fname); 
		set_multiple(tname, cl[i].name, {'amount':flt(flt(cl[i].qty) * flt(cl[i][rate_fld]))}, fname);
		set_multiple(tname, cl[i].name, {'import_amount': flt(flt(cl[i].qty) *	flt(cl[i][rate_fld]) / flt(doc.conversion_rate))}, fname); 
	}else if( n==5){	
		tmp[rate_fld] = flt( flt(cl[i].import_ref_rate) - flt(flt(cl[i].import_ref_rate)*flt(cl[i].discount_rate)/100) ) * flt(doc.conversion_rate);
		set_multiple(tname, cl[i].name, {'purchase_ref_rate': flt(flt(cl[i].import_ref_rate) * flt(doc.conversion_rate))}, fname);
		set_multiple(tname, cl[i].name, tmp, fname);
		set_multiple(tname, cl[i].name, {'import_rate': flt(flt(cl[i][rate_fld]) / flt(doc.conversion_rate))}, fname); 
		set_multiple(tname, cl[i].name, {'amount':flt(flt(cl[i].qty) * flt(cl[i][rate_fld]))}, fname);
		set_multiple(tname, cl[i].name, {'import_amount': flt(flt(cl[i].qty) *	flt(cl[i][rate_fld]) / flt(doc.conversion_rate))}, fname); 
	}
	
		if (n != 3){
			net_total += flt(flt(cl[i].qty) * flt(cl[i][rate_fld]));
			net_total_import += flt(flt(cl[i].qty) * flt(cl[i].import_rate));
		} else if(n == 3){
			net_total += flt(cl[i].amount);
			net_total_import += flt(cl[i].amount) / flt(doc.conversion_rate);
		}
		//update stock uom
		cur_frm.cscript.update_stock_qty(doc, tname, cl[i].name);
	}
	doc.net_total = flt(net_total) ;
	doc.net_total_import = flt(net_total_import) ;
	refresh_field('net_total');
	refresh_field('net_total_import');
	
	cur_frm.cscript.val_cal_charges(doc, tname, fname, other_fname);
}


//======== Function was broken away from cur_frm.cscript.calc_amount as PV has fieldname 'rate' instead of 'purchase_rate'===========
cur_frm.cscript.val_cal_charges = function(doc, tname, fname, other_fname){

	doc = locals[doc.doctype][doc.name]
	if(flt(doc.net_total) > 0) {
		var cl = getchildren('Purchase Taxes and Charges', doc.name, other_fname,doc.doctype);
		for(var i = 0; i<cl.length; i++){
			cl[i].total_tax_amount = 0;
			cl[i].total_amount = 0;
			cl[i].tax_amount = 0;										// this is done to calculate other charges
			cl[i].total = 0;
			cl[i].item_wise_tax_detail = "";
			if(in_list(['On Previous Row Amount','On Previous Row Total'],cl[i].charge_type) && !cl[i].row_id){
				alert("Please Enter Row on which amount needs to be calculated for row : "+cl[i].idx);
				validated = false;
			}
		}
		cur_frm.cscript.calc_other_charges(doc , tname , fname , other_fname); // calculate other charges
	}
	cur_frm.cscript.calc_doc_values(doc, tname, fname, other_fname); // calculates total amounts

	refresh_many(['net_total', 'grand_total', 'rounded_total', 'grand_total_import', 'rounded_total_import', 'in_words', 'in_words_import', 'purchase_tax_details', 'total_tax', 'other_charges_added', 'other_charges_deducted', 'net_total_import', 'other_charges_added_import', 'other_charges_deducted_import']);

}


// ******************************* OTHER CHARGES *************************************
cur_frm.cscript.calc_other_charges = function(doc , tname , fname , other_fname) {
	doc = locals[doc.doctype][doc.name];
	// make display area
	// ------------------

	
	cur_frm.fields_dict['tax_calculation'].disp_area.innerHTML = '<b style="padding: 8px 0px;">Calculation Details for Taxes, Charges and Landed Cost:</b>';
	var cl = getchildren(tname, doc.name, fname);
	var tax = getchildren('Purchase Taxes and Charges', doc.name, other_fname,doc.doctype);
	// make display table
	// ------------------
	var otc = make_table(cur_frm.fields_dict['tax_calculation'].disp_area, cl.length + 1, tax.length + 1, '90%',[],{border:'1px solid #AAA',padding:'2px'});
	$y(otc,{marginTop:'8px'});
	
	var tax_desc = {}; var tax_desc_rates = []; var net_total = 0;
	
	
	for(var i=0;i<cl.length;i++) {
		var item_tax = 0;
		if(doc.doctype != 'Purchase Invoice') net_total += flt(flt(cl[i].qty) * flt(cl[i].purchase_rate));
		else if(doc.doctype == 'Purchase Invoice') net_total += flt(flt(cl[i].qty) * flt(cl[i].rate));

		var prev_total = flt(cl[i].amount);
		if(cl[i].item_tax_rate) {
			try {
				var check_tax = JSON.parse(cl[i].item_tax_rate);				//to get in dictionary
			} catch(exception) {
				var check_tax = eval('var a='+cl[i].item_tax_rate+';a');        //to get in dictionary				 
			}
		}
		
		// Add Item Code in new Row 
		//--------------------------
		$td(otc,i+1,0).innerHTML = cl[i].item_code;
		
		var tax = getchildren('Purchase Taxes and Charges', doc.name, other_fname,doc.doctype);
		var total = net_total;
		for(var t=0;t<tax.length;t++){
 
			var account = tax[t].account_head;
			$td(otc,0,t+1).innerHTML = account?account:'';
			//Check For Rate
			if(cl[i].item_tax_rate && check_tax[account]!=null)	{rate = flt(check_tax[account]);}
			else							 // if particular item doesn't have particular rate it will take other charges rate
				rate = flt(tax[t].rate);

			//Check For Rate and get tax amount
			var tax_amount = cur_frm.cscript.check_charge_type_and_get_tax_amount(doc,tax,t, cl[i], rate);
			
			//enter item_wise_tax_detail i.e. tax rate on each item
			
			item_wise_tax_detail = cur_frm.cscript.get_item_wise_tax_detail( doc, rate, cl, i, tax, t);
			
			
			if(tax[t].add_deduct_tax == 'Add'){
				// this is calculation part for all types
				if(tax[t].charge_type != "Actual") tax[t].item_wise_tax_detail += item_wise_tax_detail;
				tax[t].total_amount = flt(tax_amount.toFixed(2));		 //stores actual tax amount in virtual field
				tax[t].total_tax_amount = flt(prev_total.toFixed(2));			//stores total amount in virtual field
				tax[t].tax_amount += flt(tax_amount.toFixed(2));			 
				var total_amount = flt(tax[t].tax_amount);
				total_tax_amount = flt(tax[t].total_tax_amount) + flt(total_amount);
				if(tax[t].category != "For Valuation"){
					set_multiple('Purchase Taxes and Charges', tax[t].name, { 'item_wise_tax_detail':tax[t].item_wise_tax_detail, 'amount':total_amount, 'total':flt(total)+flt(tax[t].tax_amount)/*_tax_amount)*/}, other_fname);
					prev_total += flt(tax[t].total_amount);
					total += flt(tax[t].tax_amount);	// for adding total to previous amount			 
				}
				else{
					set_multiple('Purchase Taxes and Charges', tax[t].name, { 'item_wise_tax_detail':tax[t].item_wise_tax_detail, 'amount':total_amount, 'total':flt(total)/*_tax_amount)*/}, other_fname);
					prev_total = prev_total;
				}
				//prev_total += flt(tax[t].total_amount);	 // for previous row total

				if(tax[t].charge_type == 'Actual')
					$td(otc,i+1,t+1).innerHTML = fmt_money(tax[t].total_amount);
				else
					$td(otc,i+1,t+1).innerHTML = '('+fmt_money(rate) + '%) ' +fmt_money(tax[t].total_amount);

				if (tax[t].category != "For Total"){
					item_tax += tax[t].total_amount;
				}
			}
			else if(tax[t].add_deduct_tax == 'Deduct'){
				// this is calculation part for all types
				if(tax[t].charge_type != "Actual") tax[t].item_wise_tax_detail += item_wise_tax_detail;
				tax[t].total_amount = flt(tax_amount.toFixed(2));		 //stores actual tax amount in virtual field
				tax[t].total_tax_amount = flt(prev_total.toFixed(2));			//stores total amount in virtual field
				tax[t].tax_amount += flt(tax_amount.toFixed(2));
				var total_amount = flt(tax[t].tax_amount);
				total_tax_amount = flt(tax[t].total_tax_amount) - flt(total_amount);
				if(tax[t].category != "For Valuation"){
					set_multiple('Purchase Taxes and Charges', tax[t].name, { 'item_wise_tax_detail':tax[t].item_wise_tax_detail, 'tax_amount':total_amount, 'total':flt(total)-flt(tax[t].tax_amount)/*_tax_amount)*/}, other_fname);
					prev_total -= flt(tax[t].total_amount); 
					total -= flt(tax[t].tax_amount);	// for adding total to previous amount			 
				}
				else{
					set_multiple('Purchase Taxes and Charges', tax[t].name, { 'item_wise_tax_detail':tax[t].item_wise_tax_detail, 'tax_amount':total_amount, 'total':flt(total)/*_tax_amount)*/}, other_fname);
					prev_total = prev_total;
				}
				//prev_total += flt(tax[t].total_amount);	 // for previous row total

				if(tax[t].charge_type == 'Actual')
					$td(otc,i+1,t+1).innerHTML = fmt_money(tax[t].total_amount);
				else
					$td(otc,i+1,t+1).innerHTML = '('+fmt_money(rate) + '%) ' +fmt_money(tax[t].total_amount);

				if (tax[t].category != "For Total"){
					item_tax -= tax[t].total_amount;
				}
			}			
			
			
		}
		set_multiple(tname, cl[i].name, {'item_tax_amount': item_tax }, fname);
	}
}




// ******* Calculation of total amounts of document (item amount + other charges)****************
cur_frm.cscript.calc_doc_values = function(doc, tname, fname, other_fname) {
	doc = locals[doc.doctype][doc.name];
	var net_total = 0; var total_tax = 0; var other_charges_added = 0; 
	var other_charges_deducted = 0;
	var cl = getchildren(tname, doc.name, fname);
	for(var i = 0; i<cl.length; i++){
		net_total += flt(cl[i].amount);
	}
	var d = getchildren('Purchase Taxes and Charges', doc.name, other_fname,doc.doctype);
	for(var j = 0; j<d.length; j++){
		if(d[j].category != 'For Valuation'){
			
			if(d[j].add_deduct_tax == 'Add'){
				other_charges_added += flt(d[j].tax_amount);
				total_tax += flt(d[j].tax_amount);
			}
			if(d[j].add_deduct_tax == 'Deduct'){
				other_charges_deducted += flt(d[j].tax_amount);
				total_tax -= flt(d[j].tax_amount);
			}
		}
	}
	doc.net_total = flt(net_total);
	doc.total_tax = flt(total_tax);

	doc.other_charges_added = flt(other_charges_added);
	doc.other_charges_deducted = flt(other_charges_deducted);
	doc.grand_total = flt(flt(net_total) + flt(other_charges_added) - flt(other_charges_deducted));
	doc.rounded_total = Math.round(doc.grand_total);
	doc.net_total_import = flt(flt(net_total) / flt(doc.conversion_rate));
	doc.other_charges_added_import = flt(flt(other_charges_added) / flt(doc.conversion_rate));
	doc.other_charges_deducted_import = flt(flt(other_charges_deducted) / flt(doc.conversion_rate));
	doc.grand_total_import = flt(flt(doc.grand_total) / flt(doc.conversion_rate));
	doc.rounded_total_import = Math.round(doc.grand_total_import);

	refresh_many(['net_total','total_taxes','grand_total']);


	if(doc.doctype == 'Purchase Invoice'){
		calculate_outstanding(doc);
	}
}

var calculate_outstanding = function(doc) {
	var t_tds_tax = 0.0;	
	doc.total_tds_on_voucher = flt(doc.ded_amount);

	// total amount to pay	
	doc.total_amount_to_pay = flt(flt(doc.net_total) + flt(doc.other_charges_added) - flt(doc.other_charges_deducted) - flt(doc.total_tds_on_voucher));
	
	// outstanding amount 
	if(doc.docstatus==0) doc.outstanding_amount = flt(doc.net_total) + flt(doc.other_charges_added) - flt(doc.other_charges_deducted) - flt(doc.total_tds_on_voucher) - flt(doc.total_advance);
	
	refresh_many(['total_tds_on_voucher','total_amount_to_pay', 'outstanding_amount']);
}


cur_frm.cscript.check_charge_type_and_get_tax_amount = function(doc, tax, t, cl, rate, print_amt) {
	doc = locals[doc.doctype][doc.name];

	var tax_amount = 0;
	if(tax[t].charge_type == 'Actual') {
		var value = flt(tax[t].rate) / flt(doc.net_total);	 // this give the ratio in which all items are divided					 
		return tax_amount = flt(value) * flt(cl.amount);
	 }	 
	else if(tax[t].charge_type == 'On Net Total') {
		return tax_amount = (flt(rate) * flt(cl.amount) / 100);
	}
	else if(tax[t].charge_type == 'On Previous Row Amount'){
		var row_no = (tax[t].row_id).toString();
		var row = (row_no).split("+");			// splits the values and stores in an array
		for(var r = 0;r<row.length;r++){
			var id = cint(row[r].replace(/^\s+|\s+$/g,""));
			tax_amount += (flt(rate) * flt(tax[id-1].total_amount) / 100);
		}
		var row_id = row_no.indexOf("/");
		if(row_id != -1) {
			rate = '';
			var row = (row_no).split("/");			// splits the values and stores in an array
			if(row.length>2) alert("You cannot enter more than 2 nos. for division");
			var id1 = cint(row[0].replace(/^\s+|\s+$/g,""));
			var id2 = cint(row[1].replace(/^\s+|\s+$/g,""));
			tax_amount = flt(tax[id1-1].total_amount) / flt(tax[id2-1].total_amount);
		}
		return tax_amount
	}
	else if(tax[t].charge_type == 'On Previous Row Total') {
		var row = cint(tax[t].row_id);
		if(tax[row-1].add_deduct_tax == 'Add'){
			return tax_amount = flt(rate) * (flt(tax[row-1].total_tax_amount)+flt(tax[row-1].total_amount)) / 100;
		 }
		else if(tax[row-1].add_deduct_tax == 'Deduct'){
			return tax_amount = flt(rate) * (flt(tax[row-1].total_tax_amount)-flt(tax[row-1].total_amount)) / 100;
		 }
	}
}

cur_frm.cscript.toggle_contact_section = function(doc) {
	doc.supplier ? unhide_field("contact_section") : hide_field("contact_section");
}