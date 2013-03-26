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
// cur_frm.cscript.other_fname - wn.require('app/accounts/doctype/sales_taxes_and_charges_master/sales_taxes_and_charges_master.js'); fieldname
// cur_frm.cscript.sales_team_fname - Sales Team fieldname

// ============== Load Default Taxes ===================
cur_frm.cscript.load_taxes = function(doc, cdt, cdn, callback) {
	// run if this is not executed from dt_map...
	doc = locals[doc.doctype][doc.name];
	if(doc.customer || getchildren('Sales Taxes and Charges', doc.name, 'other_charges', doc.doctype).length) {
		if(callback) {
			callback(doc, cdt, cdn);
		}
	} else if(doc.charge) {
		cur_frm.cscript.get_charges(doc, cdt, cdn, callback);
	} else {
		$c_obj(make_doclist(doc.doctype, doc.name),'load_default_taxes','',function(r,rt){
			refresh_field('other_charges');
			if(callback) callback(doc, cdt, cdn);
		});
	}
}


// Gets called after existing item details are update to fill in
// remaining default values
cur_frm.cscript.load_defaults = function(doc, dt, dn, callback) {
	if(!cur_frm.doc.__islocal) { return; }

	doc = locals[doc.doctype][doc.name];
	var fields_to_refresh = wn.model.set_default_values(doc);
	if(fields_to_refresh) { refresh_many(fields_to_refresh); }

	fields_to_refresh = null;
	var children = getchildren(cur_frm.cscript.tname, doc.name, cur_frm.cscript.fname);
	if(!children) { return; }
	for(var i=0; i<children.length; i++) {
		wn.model.set_default_values(children[i]);
	}
	refresh_field(cur_frm.cscript.fname);
	cur_frm.cscript.load_taxes(doc, dt, dn, callback);
}


// Update existing item details
cur_frm.cscript.update_item_details = function(doc, dt, dn, callback) {
	doc = locals[doc.doctype][doc.name];
	if(!cur_frm.doc.__islocal) return;
	var children = getchildren(cur_frm.cscript.tname, doc.name, cur_frm.cscript.fname);
	if(children.length) {
		$c_obj(make_doclist(doc.doctype, doc.name), 'get_item_details', '',
		function(r, rt) {
			if(!r.exc) {
				refresh_field(cur_frm.cscript.fname);
				doc = locals[doc.doctype][doc.name];
				cur_frm.cscript.load_defaults(doc, dt, dn, callback);
			}
		});
	} else {
		cur_frm.cscript.load_taxes(doc, dt, dn, callback);
	}
}


var set_dynamic_label_par = function(doc, cdt, cdn, base_curr) {
	//parent flds
	par_cols_base = {'net_total': 'Net Total', 'other_charges_total': 'Taxes and Charges Total', 
		'grand_total':	'Grand Total', 'rounded_total': 'Rounded Total', 'in_words': 'In Words'}
	par_cols_export = {'grand_total_export': 'Grand Total', 'rounded_total_export':	'Rounded Total', 'in_words_export':	'In Words'};

	for (d in par_cols_base) cur_frm.fields_dict[d].label_span.innerHTML = par_cols_base[d]+' (' + base_curr + ')';
	for (d in par_cols_export) cur_frm.fields_dict[d].label_span.innerHTML = par_cols_export[d]+' (' + doc.currency + ')';
	cur_frm.fields_dict['conversion_rate'].label_span.innerHTML = "Conversion Rate (" + doc.currency +' -> '+ base_curr + ')';
	cur_frm.fields_dict['plc_conversion_rate'].label_span.innerHTML = 'Price List Currency Conversion Rate (' + doc.price_list_currency +' -> '+ base_curr + ')';

	if (doc.doctype == 'Sales Invoice') {
		si_cols = {'total_advance': 'Total Advance', 'outstanding_amount': 'Outstanding Amount', 'paid_amount': 'Paid Amount', 'write_off_amount': 'Write Off Amount'}
		for (d in si_cols) cur_frm.fields_dict[d].label_span.innerHTML = si_cols[d] + ' (' + base_curr + ')';
	}
}


var set_dynamic_label_child = function(doc, cdt, cdn, base_curr) {
	// item table flds
	item_cols_base = {'basic_rate': 'Basic Rate', 'base_ref_rate': 'Price List Rate', 'amount': 'Amount'};
	item_cols_export = {'export_rate': 'Basic Rate', 'ref_rate': 'Price List Rate', 'export_amount': 'Amount'};
		
	for (d in item_cols_base) $('[data-grid-fieldname="'+cur_frm.cscript.tname+'-'+d+'"]').html(item_cols_base[d]+' ('+base_curr+')');
	for (d in item_cols_export) $('[data-grid-fieldname="'+cur_frm.cscript.tname+'-'+d+'"]').html(item_cols_export[d]+' ('+doc.currency+')');	

	var hide = (doc.currency == sys_defaults['currency']) ? false : true;
	for (f in item_cols_base) {
		cur_frm.fields_dict[cur_frm.cscript.fname].grid.set_column_disp(f, hide);
	}

	//tax table flds
	tax_cols = {'tax_amount': 'Amount', 'total': 'Total'};
	for (d in tax_cols) $('[data-grid-fieldname="Sales Taxes and Charges-'+d+'"]').html(tax_cols[d]+' ('+base_curr+')');
		
	if (doc.doctype == 'Sales Invoice') {
		// advance table flds
		adv_cols = {'advance_amount': 'Advance Amount', 'allocated_amount': 'Allocated Amount'}
		for (d in adv_cols) $('[data-grid-fieldname="Sales Invoice Advance-'+d+'"]').html(adv_cols[d]+' ('+base_curr+')');	
	}
}

// Change label dynamically based on currency
//------------------------------------------------------------------

cur_frm.cscript.dynamic_label = function(doc, cdt, cdn, base_curr, callback) {
	cur_frm.cscript.base_currency = base_curr;
	set_dynamic_label_par(doc, cdt, cdn, base_curr);
	set_dynamic_label_child(doc, cdt, cdn, base_curr);
	set_sales_bom_help(doc);

	if (callback) callback(doc, cdt, cdn);
}

// Help for Sales BOM items
var set_sales_bom_help = function(doc) {
	if(!cur_frm.fields_dict.packing_list) return;
	if (getchildren('Delivery Note Packing Item', doc.name, 'packing_details').length) {
		$(cur_frm.fields_dict.packing_list.row.wrapper).toggle(true);
		
		if (inList(['Delivery Note', 'Sales Invoice'], doc.doctype)) {
			help_msg = "<div class='alert'> \
				For 'Sales BOM' items, warehouse, serial no and batch no \
				will be considered from the 'Packing List' table. \
				If warehouse and batch no are same for all packing items for any 'Sales BOM' item, \
				those values can be entered in the main item table, values will be copied to 'Packing List' table. \
			</div>";
			wn.meta.get_docfield(doc.doctype, 'sales_bom_help', doc.name).options = help_msg;
		} 
	} else {
		$(cur_frm.fields_dict.packing_list.row.wrapper).toggle(false);
		if (inList(['Delivery Note', 'Sales Invoice'], doc.doctype)) {
			wn.meta.get_docfield(doc.doctype, 'sales_bom_help', doc.name).options = '';
		}
	}
	refresh_field('sales_bom_help');
}


// hide / unhide price list currency based on availability of price list in customer's currency
//---------------------------------------------------------------------------------------------------

cur_frm.cscript.hide_price_list_currency = function(doc, cdt, cdn, callback1) {
	if (doc.price_list_name && doc.currency) {
		wn.call({
			method: 'selling.doctype.sales_common.sales_common.get_price_list_currency',
			args: {'price_list':doc.price_list_name, 'company': doc.company},
			callback: function(r, rt) {
				pl_currency = r.message[0]?r.message[0]:[];
				unhide_field(['price_list_currency', 'plc_conversion_rate']);
				
				if (pl_currency.length==1) {
					if (doc.price_list_currency != pl_currency[0]) 
						set_multiple(cdt, cdn, {price_list_currency:pl_currency[0]});
					if (pl_currency[0] == doc.currency) {
						if(doc.plc_conversion_rate != doc.conversion_rate) 
							set_multiple(cdt, cdn, {plc_conversion_rate:doc.conversion_rate});
						hide_field(['price_list_currency', 'plc_conversion_rate']);
					} else if (pl_currency[0] == r.message[1]) {
						if (doc.plc_conversion_rate != 1) 
							set_multiple(cdt, cdn, {plc_conversion_rate:1})
						hide_field(['price_list_currency', 'plc_conversion_rate']);
					}
				}

				if (r.message[1] == doc.currency) {
					if (doc.conversion_rate != 1) 
						set_multiple(cdt, cdn, {conversion_rate:1});
					hide_field(['conversion_rate', 'grand_total_export', 'in_words_export', 'rounded_total_export']);
				} else {
					unhide_field(['conversion_rate', 'grand_total_export', 'in_words_export']);
					if(!cint(sys_defaults.disable_rounded_total))
						unhide_field("rounded_total_export");
				}
				if (r.message[1] == doc.price_list_currency) {
					if (doc.plc_conversion_rate != 1) 
						set_multiple(cdt, cdn, {plc_conversion_rate:1});
					hide_field('plc_conversion_rate');
				} else unhide_field('plc_conversion_rate');
				cur_frm.cscript.dynamic_label(doc, cdt, cdn, r.message[1], callback1);	
			}
		})
	}
}

cur_frm.cscript.manage_rounded_total = function() {
	if(cint(sys_defaults.disable_rounded_total)) {
		cur_frm.set_df_property("rounded_total", "print_hide", 1);
		cur_frm.set_df_property("rounded_total_export", "print_hide", 1);
		hide_field(["rounded_total", "rounded_total_export"]);
	}
}

// TRIGGERS FOR CALCULATIONS
// =====================================================================================================

// ********************* CURRENCY ******************************
cur_frm.cscript.currency = function(doc, cdt, cdn) {
	cur_frm.cscript.price_list_name(doc, cdt, cdn); 
}

cur_frm.cscript.price_list_currency = cur_frm.cscript.currency;
cur_frm.cscript.conversion_rate = cur_frm.cscript.currency;
cur_frm.cscript.plc_conversion_rate = cur_frm.cscript.currency;

cur_frm.cscript.company = function(doc, cdt, cdn) {
	wn.call({
		method: 'selling.doctype.sales_common.sales_common.get_comp_base_currency',
		args: {company:doc.company},
		callback: function(r, rt) {
			var doc = locals[cdt][cdn];
			set_multiple(doc.doctype, doc.name, {
				currency:r.message, 
				price_list_currency:r.message
			});
			cur_frm.cscript.currency(doc, cdt, cdn);
		}
	});
}



// ******************** PRICE LIST ******************************
cur_frm.cscript.price_list_name = function(doc, cdt, cdn) {
	var callback = function() {
		var fname = cur_frm.cscript.fname;
		var cl = getchildren(cur_frm.cscript.tname, doc.name, cur_frm.cscript.fname);
		if(doc.price_list_name && doc.currency && doc.price_list_currency && doc.conversion_rate && doc.plc_conversion_rate) {
			$c_obj(make_doclist(doc.doctype, doc.name), 'get_adj_percent', '',
				function(r, rt) {
					refresh_field(fname);
					var doc = locals[cdt][cdn];
					cur_frm.cscript.recalc(doc,3);		//this is to re-calculate BASIC RATE and AMOUNT on basis of changed REF RATE
				}
			);
		}
	}
	cur_frm.cscript.hide_price_list_currency(doc, cdt, cdn, callback);
}



// ******************** ITEM CODE ******************************** 
cur_frm.fields_dict[cur_frm.cscript.fname].grid.get_field("item_code").get_query = function(doc, cdt, cdn) {
	if (inList(['Maintenance', 'Service'], doc.order_type)) {
	 	return erpnext.queries.item({
			'ifnull(tabItem.is_service_item, "No")': 'Yes'
		});
	} else {
		return erpnext.queries.item({
			'ifnull(tabItem.is_sales_item, "No")': 'Yes'
		});
	}
}


cur_frm.cscript.item_code = function(doc, cdt, cdn) {
	var fname = cur_frm.cscript.fname;
	var d = locals[cdt][cdn];
	if (d.item_code) {
		if (!doc.company) {
			msgprint("Please select company to proceed");
			d.item_code = '';
			refresh_field('item_code', d.name, fname);
		} else {
			var callback = function(r, rt){
				cur_frm.cscript.recalc(doc, 1);
			}
			var args = {
				'item_code':d.item_code, 
				'income_account':d.income_account, 
				'cost_center': d.cost_center, 
				'warehouse': d.warehouse
			};
			get_server_fields('get_item_details',JSON.stringify(args), 
				fname,doc,cdt,cdn,1,callback);
		}
	}
	if(cur_frm.cscript.custom_item_code){
		cur_frm.cscript.custom_item_code(doc, cdt, cdn);
	}
}

//Barcode
//
cur_frm.cscript.barcode = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	var callback = function(r, rt) {
		cur_frm.cscript.item_code(doc, cdt, cdn);
	}
	if(d.barcode) {
		get_server_fields('get_barcode_details', d.barcode, cur_frm.cscript.fname, 
		doc, cdt, cdn, 1, callback);
	}
}

cur_frm.fields_dict[cur_frm.cscript.fname].grid.get_field('batch_no').get_query = 
	function(doc, cdt, cdn) {
		var d = locals[cdt][cdn];
		if(d.item_code) {
			if (d.warehouse) {
				return "select batch_no from `tabStock Ledger Entry` sle \
					where item_code = '" + d.item_code + "' and warehouse = '" + d.warehouse +
					"' and ifnull(is_cancelled, 'No') = 'No' and batch_no like '%s' \
					and exists(select * from `tabBatch` where \
					name = sle.batch_no and expiry_date >= '" + doc.posting_date + 
					"' and docstatus != 2) group by batch_no having sum(actual_qty) > 0 \
					order by batch_no desc limit 50";
			} else {
				return "SELECT name FROM tabBatch WHERE docstatus != 2 AND item = '" + 
					d.item_code + "' and expiry_date >= '" + doc.posting_date + 
					"' AND name like '%s' ORDER BY name DESC LIMIT 50";
			}		
		} else {
			msgprint("Please enter Item Code to get batch no");
		}
	}

cur_frm.fields_dict.customer_address.on_new = function(dn) {
	locals['Address'][dn].customer = locals[cur_frm.doctype][cur_frm.docname].customer;
	locals['Address'][dn].customer_name = locals[cur_frm.doctype][cur_frm.docname].customer_name;
}

cur_frm.fields_dict.contact_person.on_new = function(dn) {
	locals['Contact'][dn].customer = locals[cur_frm.doctype][cur_frm.docname].customer;
	locals['Contact'][dn].customer_name = locals[cur_frm.doctype][cur_frm.docname].customer_name;
}

cur_frm.fields_dict['customer_address'].get_query = function(doc, cdt, cdn) {
	return 'SELECT name, address_line1, city FROM tabAddress \
		WHERE customer = "'+ doc.customer +'" AND docstatus != 2 AND \
		%(key)s LIKE "%s" ORDER BY name ASC LIMIT 50';
}

cur_frm.fields_dict['contact_person'].get_query = function(doc, cdt, cdn) {
	return 'SELECT name, CONCAT(first_name," ",ifnull(last_name,"")) As FullName, \
		department, designation FROM tabContact WHERE customer = "'+ doc.customer + 
		'" AND docstatus != 2 AND %(key)s LIKE "%s" ORDER BY name ASC LIMIT 50';
}

// *********************** QUANTITY ***************************
cur_frm.cscript.qty = function(doc, cdt, cdn) { cur_frm.cscript.recalc(doc, 1); }
	
// ************************ DISCOUNT (%) ***********************
cur_frm.cscript.adj_rate = function(doc, cdt, cdn) { cur_frm.cscript.recalc(doc, 1); }

// ************************ REF RATE ****************************
cur_frm.cscript.ref_rate = function(doc, cdt, cdn){
	var d = locals[cdt][cdn];
	var consider_incl_rate = cur_frm.cscript.consider_incl_rate(doc, cur_frm.cscript.other_fname);
	if(!consider_incl_rate) {
		set_multiple(cur_frm.cscript.tname, d.name, {'export_rate': flt(d.ref_rate) * (100 - flt(d.adj_rate)) / 100}, cur_frm.cscript.fname);
	}
	cur_frm.cscript.recalc(doc, 1);
}

// *********************** BASIC RATE **************************
cur_frm.cscript.basic_rate = function(doc, cdt, cdn) { 
	var fname = cur_frm.cscript.fname;
	var d = locals[cdt][cdn];
	if(!d.qty) {
		d.qty = 1;
		refresh_field('qty', d.name, fname);
	}
	var consider_incl_rate = cur_frm.cscript.consider_incl_rate(doc, cur_frm.cscript.other_fname);
	if(!consider_incl_rate) {
		cur_frm.cscript.recalc(doc, 2);
	} else {
		var basic_rate = cur_frm.cscript.back_calc_basic_rate(
			doc, cur_frm.cscript.tname, fname, d, cur_frm.cscript.other_fname
		);
		// TODO: remove roundNumber for basic_rate comparison
		if (d.basic_rate != roundNumber(basic_rate, 2)) { 
			d.basic_rate = basic_rate;
			refresh_field('basic_rate', d.name, fname); 
			msgprint("You cannot change Basic Rate* (Base Currency) when \
				considering rates inclusive of taxes.<br /> \
				Please either <br /> \
				* Specify Basic Rate (i.e. Rate which will be displayed in print) <br /> \
				-- or -- <br />\
				* Uncheck 'Is this Tax included in Basic Rate?' in the tax entries of Taxes section.");
		}
	}
}

// ************************ EXPORT RATE *************************
cur_frm.cscript.export_rate = function(doc,cdt,cdn) {
	var cur_rec = locals[cdt][cdn];
	var fname = cur_frm.cscript.fname;
	var tname = cur_frm.cscript.tname;
	if(flt(cur_rec.ref_rate)>0 && flt(cur_rec.export_rate)>0) {
		var adj_rate = 100 * (1 - (flt(cur_rec.export_rate) / flt(cur_rec.ref_rate)));
		set_multiple(tname, cur_rec.name, { 'adj_rate': adj_rate }, fname);
	}
	doc = locals[doc.doctype][doc.name];
	cur_frm.cscript.recalc(doc, 1);
}



// ************* GET OTHER CHARGES BASED ON COMPANY *************
cur_frm.fields_dict.charge.get_query = function(doc) {
	return 'SELECT DISTINCT `tabSales Taxes and Charges Master`.name FROM \
		`tabSales Taxes and Charges Master` WHERE `tabSales Taxes and Charges Master`.company = "'
		+doc.company+'" AND `tabSales Taxes and Charges Master`.company is not NULL \
		AND `tabSales Taxes and Charges Master`.docstatus != 2 \
		AND `tabSales Taxes and Charges Master`.%(key)s LIKE "%s" \
		ORDER BY `tabSales Taxes and Charges Master`.name LIMIT 50';
}

// ********************* Get Charges ****************************
cur_frm.cscript.get_charges = function(doc, cdt, cdn, callback) {
	$c_obj(make_doclist(doc.doctype,doc.name),
		'get_other_charges',
		'', 
		function(r, rt) {
			cur_frm.cscript.calculate_charges(doc, cdt, cdn);
			if(callback) callback(doc, cdt, cdn);
		}, null,null,cur_frm.fields_dict.get_charges.input);
}


// CALCULATION OF TOTAL AMOUNTS
// ======================================================================================================== 
cur_frm.cscript.recalc = function(doc, n) {
	if(!n)n=0;
	doc = locals[doc.doctype][doc.name];
	var tname = cur_frm.cscript.tname;
	var fname = cur_frm.cscript.fname;
	var sales_team = cur_frm.cscript.sales_team_fname;
	var other_fname	= cur_frm.cscript.other_fname;
	
	if(!flt(doc.conversion_rate)) { 
		doc.conversion_rate = 1; 
		refresh_field('conversion_rate'); 
	}
	if(!flt(doc.plc_conversion_rate)) { 
		doc.plc_conversion_rate = 1; 
		refresh_field('plc_conversion_rate'); 
	}

	if(n > 0) cur_frm.cscript.update_fname_table(doc , tname , fname , n, other_fname); // updates all values in table (i.e. amount, export amount, net total etc.)
	
	if(flt(doc.net_total) > 0) {
		var cl = getchildren('Sales Taxes and Charges', doc.name, other_fname,doc.doctype);
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
	cur_frm.cscript.calc_doc_values(doc, null, null, tname, fname, other_fname); // calculates total amounts

	// ******************* calculate allocated amount of sales person ************************
	cl = getchildren('Sales Team', doc.name, sales_team);
	for(var i=0;i<cl.length;i++) {
		if (cl[i].allocated_percentage) {
			cl[i].allocated_amount = flt(flt(doc.net_total)*flt(cl[i].allocated_percentage)/100);
			refresh_field('allocated_amount', cl[i].name, sales_team);
		}
	}
	doc.in_words = '';
	doc.in_words_export = '';
	refresh_many(['total_discount_rate','total_discount','net_total','total_commission','grand_total','rounded_total','grand_total_export','rounded_total_export','in_words','in_words_export','other_charges','other_charges_total']);
	if(cur_frm.cscript.custom_recalc)cur_frm.cscript.custom_recalc(doc);
}

// ******* Calculation of total amounts of document (item amount + other charges)****************
cur_frm.cscript.calc_doc_values = function(doc, cdt, cdn, tname, fname, other_fname) {
	doc = locals[doc.doctype][doc.name];
	var net_total = 0; var other_charges_total = 0;
	var net_total_incl = 0
	var cl = getchildren(tname, doc.name, fname);
	for(var i = 0; i<cl.length; i++){
		//net_total += flt(cl[i].basic_rate) * flt(cl[i].qty);
		net_total += flt(cl[i].amount);
		net_total_incl += flt(cl[i].export_amount);
	}

	var inclusive_rate = 0
	var d = getchildren('Sales Taxes and Charges', doc.name, other_fname,doc.doctype);
	for(var j = 0; j<d.length; j++){
		other_charges_total += flt(d[j].tax_amount);
		if(d[j].included_in_print_rate) {
			inclusive_rate = 1;
		}
	}

	if(flt(doc.conversion_rate)>1) {
		net_total_incl *= flt(doc.conversion_rate);
	}

	doc.net_total = inclusive_rate ? flt(net_total_incl) : flt(net_total);
	doc.other_charges_total = roundNumber(flt(other_charges_total), 2);
	doc.grand_total = roundNumber((flt(net_total) + flt(other_charges_total)), 2);
	doc.rounded_total = Math.round(doc.grand_total);
	doc.grand_total_export = roundNumber((flt(doc.grand_total) / flt(doc.conversion_rate)), 2);
	doc.rounded_total_export = Math.round(doc.grand_total_export);
	doc.total_commission = flt(flt(net_total) * flt(doc.commission_rate) / 100);
}

// ******************************* OTHER CHARGES *************************************
cur_frm.cscript.calc_other_charges = function(doc , tname , fname , other_fname) {
	doc = locals[doc.doctype][doc.name];

	// Make Display Area
	cur_frm.fields_dict['other_charges_calculation'].disp_area.innerHTML =
		'<b style="padding: 8px 0px;">Calculation Details for Taxes and Charges:</b>';

	var cl = getchildren(tname, doc.name, fname);
	var tax = getchildren('Sales Taxes and Charges', doc.name, other_fname,doc.doctype);
	
	// Make display table
	var otc = make_table(cur_frm.fields_dict['other_charges_calculation'].disp_area,
		cl.length + 1, tax.length + 1, '90%', [], { border:'1px solid #AAA', padding:'2px' });
	$y(otc,{marginTop:'8px'});

	var tax_desc = {}; var tax_desc_rates = []; var net_total = 0;
	
	for(var i=0;i<cl.length;i++) {
		net_total += flt(flt(cl[i].qty) * flt(cl[i].basic_rate));
		var prev_total = flt(cl[i].amount);
		if(cl[i].item_tax_rate) {
			try {
				var check_tax = JSON.parse(cl[i].item_tax_rate);				//to get in dictionary
			} catch(exception) {
				var check_tax = eval('var a='+cl[i].item_tax_rate+';a');        //to get in dictionary
			}
		}
		
		// Add Item Code in new Row
		$td(otc,i+1,0).innerHTML = cl[i].item_code ? cl[i].item_code : cl[i].description;
		
		//var tax = getchildren('Sales Taxes and Charges', doc.name, other_fname,doc.doctype);
		var total = net_total;
		
		
		for(var t=0;t<tax.length;t++){
			var account = tax[t].account_head;
			$td(otc,0,t+1).innerHTML = account?account:'';
			//Check For Rate
			if(cl[i].item_tax_rate && check_tax[account]!=null) {
				var rate = flt(check_tax[account]);
			} else {
				// if particular item doesn't have particular rate it will take other charges rate
				var rate = flt(tax[t].rate);
			}

			//Check For Rate and get tax amount
			var tax_amount = cur_frm.cscript.check_charge_type_and_get_tax_amount(doc,tax,t, cl[i], rate);
			
			//enter item_wise_tax_detail i.e. tax rate on each item
			var item_wise_tax_detail = cur_frm.cscript.get_item_wise_tax_detail(doc, rate, cl, i, tax, t);
			if(tax[t].charge_type != "Actual") tax[t].item_wise_tax_detail += item_wise_tax_detail;
			tax[t].total_amount = flt(tax_amount);		 //stores actual tax amount in virtual field
			tax[t].total_tax_amount = flt(prev_total);			//stores total amount in virtual field
			tax[t].tax_amount += flt(tax_amount);			 
			var total_amount = flt(tax[t].tax_amount);
			total_tax_amount = flt(tax[t].total_tax_amount) + flt(total_amount);
			set_multiple('Sales Taxes and Charges', tax[t].name, { 'item_wise_tax_detail':tax[t].item_wise_tax_detail, 'amount':roundNumber(flt(total_amount), 2), 'total':roundNumber(flt(total)+flt(tax[t].tax_amount), 2)}, other_fname);
			prev_total += flt(tax[t].total_amount);	 // for previous row total
			total += flt(tax[t].tax_amount);		 // for adding total to previous amount

			if(tax[t].charge_type == 'Actual')
				$td(otc,i+1,t+1).innerHTML = format_currency(tax[t].total_amount, erpnext.get_currency(doc.company));
			else
				$td(otc,i+1,t+1).innerHTML = '('+format_number(rate) + '%) ' +format_currency(tax[t].total_amount, erpnext.get_currency(doc.company));

		}
	}
	
	for(var t=0;t<tax.length;t++){
		tax[t].tax_amount = roundNumber(tax[t].tax_amount, 2);
	}
}
cur_frm.cscript.check_charge_type_and_get_tax_amount = function( doc, tax, t, cl, rate, print_amt) {
	doc = locals[doc.doctype][doc.name];
	if (! print_amt) print_amt = 0;
	var tax_amount = 0;
	if(tax[t].charge_type == 'Actual') {
		var value = flt(tax[t].rate) / flt(doc.net_total);	 // this give the ratio in which all items are divided					 
		return tax_amount = flt(value) * flt(cl.amount);
	 }	 
	else if(tax[t].charge_type == 'On Net Total') {
		if (flt(print_amt) == 1) {
			doc.excise_rate = flt(rate);
			doc.total_excise_rate += flt(rate);
			refresh_field('excise_rate');
			refresh_field('total_excise_rate');
			return
		}
	return tax_amount = (flt(rate) * flt(cl.amount) / 100);
	}
	else if(tax[t].charge_type == 'On Previous Row Amount'){
		if(flt(print_amt) == 1) {
			doc.total_excise_rate += flt(flt(doc.excise_rate) * 0.01 * flt(rate));
			refresh_field('total_excise_rate');
			return
		}
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
		if(flt(print_amt) == 1) {
			doc.sales_tax_rate += flt(rate);
			refresh_field('sales_tax_rate');
			return
		}
		var row = cint(tax[t].row_id);
		return tax_amount = flt(rate) * (flt(tax[row-1].total_tax_amount)+flt(tax[row-1].total_amount)) / 100;
	}
}

// ********************** Functions for inclusive value calc ******************************
cur_frm.cscript.consider_incl_rate = function(doc, other_fname) {
	var tax_list = getchildren('Sales Taxes and Charges', doc.name, other_fname, doc.doctype);
	for(var i=0; i<tax_list.length; i++) {
		if(tax_list[i].included_in_print_rate) {
			return true;
		}
	}
	return false;
}

cur_frm.cscript.back_calc_basic_rate = function(doc, tname, fname, child, other_fname) {	
	var get_item_tax_rate = function(item, tax) {
		if(item.item_tax_rate) {
			try {
				var item_tax = JSON.parse(item.item_tax_rate);
			} catch(exception) {
				var item_tax = eval('var a='+item.item_tax_rate+';a');
			}
			if(item_tax[tax.account_head]!=null) {
				return flt(item_tax[tax.account_head]);
			}
		}
	};

	var tax_list = getchildren('Sales Taxes and Charges', doc.name, other_fname, doc.doctype);
	var total = 1;
	var temp_tax_list = [];
	var amt = 0;
	var item_tax_rate = 0;
	var rate = 0;
	for(var i=0; i<tax_list.length; i++) {
		amt = 0;
		item_tax_rate = get_item_tax_rate(child, tax_list[i]);
		rate = item_tax_rate ? item_tax_rate : flt(tax_list[i].rate);
		if(tax_list[i].included_in_print_rate) {
			if(tax_list[i].charge_type=='On Net Total') {
				amt = flt(rate / 100);
			} else if(tax_list[i].charge_type=='On Previous Row Total') {
				amt = flt((rate * temp_tax_list[tax_list[i].row_id-1]['total']) / 100);
			} else if(tax_list[i].charge_type=='On Previous Row Amount') {
				amt = flt((rate * temp_tax_list[tax_list[i].row_id-1]['amt']) / 100);
			}
		}
		total += flt(amt);
		temp_tax_list[i] = {
			amt: amt,
			total: total
		};
	}
	var basic_rate = (child.export_rate * flt(doc.conversion_rate)) / total;
	//console.log(temp_tax_list);
	//console.log('in basic rate back calc');
	//console.log(basic_rate);
	return basic_rate;
}

cur_frm.cscript.included_in_print_rate = function(doc, cdt, cdn) {
	var tax = locals[cdt][cdn];
	if(tax.included_in_print_rate==1) { 
		if(!inList(['On Net Total', 'On Previous Row Total', 'On Previous Row Amount'], tax.charge_type)) {
			msgprint("'Is this Tax included in Basic Rate?' (i.e. Inclusive Price) is only valid for charges of type: <br /> \
				* On Net Total <br /> \
				* On Previous Row Amount <br /> \
				* On Previous Row Total");
			tax.included_in_print_rate = 0;
			refresh_field('included_in_print_rate', tax.name, cur_frm.cscript.other_fname);
		} 
		var tax_list = getchildren('Sales Taxes and Charges', doc.name, cur_frm.cscript.other_fname, doc.doctype);
		cur_frm.cscript.validate_print_rate_option(doc, tax_list, tax.idx-1);
	}
}

// ********************** Update values in table ******************************
cur_frm.cscript.update_fname_table = function(doc , tname , fname , n, other_fname) {
	doc = locals[doc.doctype][doc.name] 
	var net_total = 0
	var cl = getchildren(tname, doc.name, fname);
	var consider_incl_rate = cur_frm.cscript.consider_incl_rate(doc, other_fname);
	for(var i=0;i<cl.length;i++) {
		if(n == 1){
			if(!consider_incl_rate) {
				if(flt(cl[i].ref_rate) > 0) {
					set_multiple(tname, cl[i].name, {
						'export_rate': flt(flt(cl[i].ref_rate) * (100 - flt(cl[i].adj_rate)) / 100)
					}, fname);
				}
				set_multiple(tname, cl[i].name, {
					'export_amount': flt(flt(cl[i].qty) * flt(cl[i].export_rate)),
					'basic_rate': flt(flt(cl[i].export_rate) * flt(doc.conversion_rate)),
					'amount': roundNumber(flt((flt(cl[i].export_rate) * flt(doc.conversion_rate)) * flt(cl[i].qty)), 2)
				}, fname);
				//var base_ref_rate = flt(cl[i].basic_rate) + flt(flt(cl[i].basic_rate) * flt(cl[i].adj_rate) / 100);
				//set_multiple(tname, cl[i].name, {
				//	'base_ref_rate': flt(base_ref_rate)
				//}, fname);

		} else if(consider_incl_rate) {
			if(flt(cl[i].export_rate) > 0) {
				// calculate basic rate based on taxes
				// then calculate and set basic_rate, base_ref_rate, ref_rate, amount, export_amount
				var ref_rate = flt(cl[i].adj_rate)!=flt(100) ?
					flt((100 * flt(cl[i].export_rate))/flt(100 - flt(cl[i].adj_rate))) :
					flt(0)
				set_multiple(tname, cl[i].name, { 'ref_rate': ref_rate }, fname);
			} else if((flt(cl[i].ref_rate) > 0) && (flt(cl[i].adj_rate) > 0)) {
				var export_rate = flt(cl[i].ref_rate) * flt(1 - flt(cl[i].adj_rate / 100));
				set_multiple(tname, cl[i].name, { 'export_rate': flt(export_rate) }, fname);
			}
			//console.log("export_rate: " + cl[i].export_rate);

			var basic_rate = cur_frm.cscript.back_calc_basic_rate(doc, tname, fname, cl[i], other_fname);
			var base_ref_rate = basic_rate + flt(basic_rate * flt(cl[i].adj_rate) / 100);
			set_multiple(tname, cl[i].name, {
				'basic_rate': flt(basic_rate),
				'amount': roundNumber(flt(basic_rate * flt(cl[i].qty)), 2),
				'export_amount': flt(flt(cl[i].qty) * flt(cl[i].export_rate)),
				'base_ref_rate': flt(base_ref_rate)
			}, fname);
		}
		}
		else if(n == 2){
			if(flt(cl[i].ref_rate) > 0)
				set_multiple(tname, cl[i].name, {'adj_rate': 100 - flt(flt(cl[i].basic_rate)	* 100 / (flt(cl[i].ref_rate) * flt(doc.conversion_rate)))}, fname);
			set_multiple(tname, cl[i].name, {'amount': flt(flt(cl[i].qty) * flt(cl[i].basic_rate)), 'export_rate': flt(flt(cl[i].basic_rate) / flt(doc.conversion_rate)), 'export_amount': flt((flt(cl[i].basic_rate) / flt(doc.conversion_rate)) * flt(cl[i].qty)) }, fname);
		}
		/*else if(n == 3){
			set_multiple(tname, cl[i].name, {'basic_rate': flt(flt(cl[i].export_rate) * flt(doc.conversion_rate))}, fname);
			set_multiple(tname, cl[i].name, {'amount' : flt(flt(cl[i].basic_rate) * flt(cl[i].qty)), 'export_amount': flt(flt(cl[i].export_rate) * flt(cl[i].qty))}, fname);
			if(cl[i].ref_rate > 0)
		set_multiple(tname, cl[i].name, {'adj_rate': 100 - flt(flt(cl[i].export_rate) * 100 / flt(cl[i].ref_rate)), 'base_ref_rate': flt(flt(cl[i].ref_rate) * flt(doc.conversion_rate)) }, fname);
		}*/
		net_total += flt(flt(cl[i].qty) * flt(cl[i].basic_rate));
	}
	doc.net_total = net_total;
	refresh_field('net_total');
}

cur_frm.cscript.get_item_wise_tax_detail = function( doc, rate, cl, i, tax, t) {
	doc = locals[doc.doctype][doc.name];
	var detail = '';
	detail = cl[i].item_code + " : " + cstr(rate) + NEWLINE;
	return detail;
}

// **************** RE-CALCULATE VALUES ***************************

cur_frm.cscript.recalculate_values = function(doc, cdt, cdn) {	
	cur_frm.cscript.calculate_charges(doc,cdt,cdn);
}

cur_frm.cscript.validate_print_rate_option = function(doc, taxes, i) {
	if(in_list(['On Previous Row Amount','On Previous Row Total'], taxes[i].charge_type)) { 
		if(!taxes[i].row_id){
			alert("Please Enter Row on which amount needs to be calculated for row : "+taxes[i].idx);
			validated = false;
		} else if(taxes[i].included_in_print_rate && taxes[taxes[i].row_id-1].charge_type=='Actual') {
			msgprint("Row of type 'Actual' cannot be depended on for type '" + taxes[i].charge_type + "'\
				when using tax inclusive prices.<br />\
				This will lead to incorrect values.<br /><br /> \
				<b>Please specify correct value in 'Enter Row' column of <span style='color:red'>Row: "	
				+ taxes[i].idx + "</span> in Taxes table</b>");
			validated = false;
			taxes[i].included_in_print_rate = 0;
			refresh_field('included_in_print_rate', taxes[i].name, other_fname);
		} else if ((taxes[i].included_in_print_rate && !taxes[taxes[i].row_id-1].included_in_print_rate) || 
			(!taxes[i].included_in_print_rate && taxes[taxes[i].row_id-1].included_in_print_rate)) {
			msgprint("If any row in the tax table depends on 'Previous Row Amount/Total', <br />\
				'Is this Tax included in Basic Rate?' column should be same for both row <br />\
				i.e for that row and the previous row. <br /><br />\
				The same is violated for row #"+(i+1)+" and row #"+taxes[i].row_id
			);
			validated = false;
		}		
	}
}

cur_frm.cscript.calculate_charges = function(doc, cdt, cdn) {
	var other_fname	= cur_frm.cscript.other_fname;

	var cl = getchildren('Sales Taxes and Charges', doc.name, other_fname, doc.doctype);
	for(var i = 0; i<cl.length; i++){
		cl[i].total_tax_amount = 0;
		cl[i].total_amount = 0;
		cl[i].tax_amount = 0;										// this is done to calculate other charges
		cl[i].total = 0;
		cur_frm.cscript.validate_print_rate_option(doc, cl, i);
	}
	cur_frm.cscript.recalc(doc, 1);
}

// Get Sales Partner Commission
// =================================================================================
cur_frm.cscript.sales_partner = function(doc, cdt, cdn){
	if(doc.sales_partner){

		get_server_fields('get_comm_rate', doc.sales_partner, '', doc, cdt, cdn, 1);
	}
}

// *******Commission Rate Trigger (calculates total commission amount)*********
cur_frm.cscript.commission_rate = function(doc, cdt, cdn) {
	if(doc.commission_rate > 100){
		alert("Commision rate cannot be greater than 100.");
		doc.total_commission = 0;
		doc.commission_rate = 0;
	} else {
		doc.total_commission = doc.net_total * doc.commission_rate / 100;
	}
	refresh_many(['total_commission','commission_rate']);

}

// *******Total Commission Trigger (calculates commission rate)*********
cur_frm.cscript.total_commission = function(doc, cdt, cdn) {
	if(doc.net_total){
		if(doc.net_total < doc.total_commission){
			alert("Total commission cannot be greater than net total.");
			doc.total_commission = 0;
			doc.commission_rate = 0;
		} else {
			doc.commission_rate = doc.total_commission * 100 / doc.net_total;
		}
		refresh_many(['total_commission','commission_rate']);
	}
}
// Sales Person Allocated % trigger 
// ==============================================================================
cur_frm.cscript.allocated_percentage = function(doc, cdt, cdn) {
	var fname = cur_frm.cscript.sales_team_fname;
	var d = locals[cdt][cdn];
	if (d.allocated_percentage) {
		d.allocated_amount = flt(flt(doc.net_total)*flt(d.allocated_percentage)/100);
		refresh_field('allocated_amount', d.name, fname);
	}
}

// Client Side Validation
// =================================================================================
cur_frm.cscript.validate = function(doc, cdt, cdn) {
	cur_frm.cscript.validate_items(doc);
	var cl = getchildren('Sales Taxes and Charges Master', doc.name, 'other_charges');
	for(var i =0;i<cl.length;i++) {
		if(!cl[i].amount) {
			alert("Please Enter Amount in Row no. "+cl[i].idx+" in Taxes and Charges table");
			validated = false;
		}
	}
	cur_frm.cscript.calculate_charges (doc, cdt, cdn);

	if (doc.docstatus == 0 && cur_frm.cscript.calc_adjustment_amount)
	 	cur_frm.cscript.calc_adjustment_amount(doc);
}


// ************** Atleast one item in document ****************
cur_frm.cscript.validate_items = function(doc) {
	var cl = getchildren(cur_frm.cscript.tname, doc.name, cur_frm.cscript.fname);
	if(!cl.length){
		alert("Please enter Items for " + doc.doctype);
		validated = false;
	}
}

cur_frm.fields_dict.customer.get_query = erpnext.utils.customer_query;