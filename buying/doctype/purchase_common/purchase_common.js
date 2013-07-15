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

wn.provide("erpnext.buying");

erpnext.buying.BuyingController = wn.ui.form.Controller.extend({
	setup: function() {
		var me = this;
		
		if(this.frm.fields_dict.price_list_name) {
			this.frm.fields_dict.price_list_name.get_query = function() {
				return repl("select distinct price_list_name from `tabItem Price` \
					where buying = 1 and price_list_name like \"%s%%\"");
			};
		}
		
		if(this.frm.fields_dict.price_list_currency) {
			this.frm.fields_dict.price_list_currency.get_query = function() {
				return repl("select distinct ref_currency from `tabItem Price` \
					where price_list_name=\"%(price_list_name)s\" and buying = 1 \
					and ref_currency like \"%s%%\"", 
					{price_list_name: me.frm.doc.price_list_name});
			};
		}
	},
	
	refresh: function() {
		this.frm.clear_custom_buttons();
		erpnext.hide_naming_series();
		
		if(this.frm.fields_dict.supplier)
			this.frm.toggle_display("contact_section", this.frm.doc.supplier);
		
		if(this.frm.fields_dict.currency)
			this.set_dynamic_labels();
	},
	
	price_list_name: function(callback_fn) {
		var me = this;
		
		if(this.frm.doc.price_list_name) {
			if(!this.frm.doc.price_list_currency) {
				// set price list currency
				this.frm.call({
					method: "setup.utils.get_price_list_currency",
					args: {args: {
						price_list_name: this.frm.doc.price_list_name,
						use_for: "buying"
					}},
					callback: function(r) {
						if(!r.exc) {
							me.price_list_currency();
							if (typeof callback_fn === "function") 
								callback_fn(me.frm.doc, me.frm.doc.doctype, me.frm.doc.name);
						}
					}
				});
			} else {
				me.price_list_currency();
				if (typeof callback_fn === "function") 
					callback_fn(me.frm.doc, me.frm.doc.doctype, me.frm.doc.name);
			}
		} 
	},
	
	item_code: function(doc, cdt, cdn) {
		var me = this;
		var item = locals[cdt][cdn];
		
		if(item.item_code) {
			this.frm.call({
				method: "buying.utils.get_item_details",
				child: item,
				args: {
					args: {
						doctype: me.frm.doc.doctype,
						docname: me.frm.doc.name,
						item_code: item.item_code,
						warehouse: item.warehouse,
						supplier: me.frm.doc.supplier,
						conversion_rate: me.frm.doc.conversion_rate,
						price_list_name: me.frm.doc.price_list_name,
						price_list_currency: me.frm.doc.price_list_currency,
						plc_conversion_rate: me.frm.doc.plc_conversion_rate
					}
				},
			});
		}
	},
	
	update_item_details: function(doc, dt, dn, callback) {
		if(!this.frm.doc.__islocal) return;
		
		var me = this;
		var children = getchildren(this.tname, this.frm.doc.name, this.fname);
		if(children && children.length) {
			this.frm.call({
				doc: me.frm.doc,
				method: "update_item_details",
				callback: function(r) {
					if(!r.exc) {
						refresh_field(me.fname);
						me.load_defaults(me.frm.doc, dt, dn, callback);
					}
				}
			})
		} else {
			this.load_taxes(doc, dt, dn, callback);
		}
	},
	
	currency: function() {
		if(this.frm.doc.currency === this.get_company_currency())
			this.frm.set_value("conversion_rate", 1.0);
		
		this.price_list_currency();
	},
	
	company: function() {
		if(this.frm.fields_dict.currency)
			this.set_dynamic_labels();
	},
	
	price_list_currency: function() {
		this.frm.toggle_reqd("plc_conversion_rate",
			!!(this.frm.doc.price_list_name && this.frm.doc.price_list_currency));
		
		if(this.frm.doc.price_list_currency === this.get_company_currency())
			this.frm.set_value("plc_conversion_rate", 1.0);
		else if(this.frm.doc.price_list_currency === this.frm.doc.currency)
			this.frm.set_value("plc_conversion_rate", this.frm.doc.conversion_rate || 1.0);		
		
		this.set_dynamic_labels();
	},
	
	set_dynamic_labels: function(doc, dt, dn) {
		var company_currency = this.get_company_currency();
		
		this.change_form_labels(company_currency);
		this.change_grid_labels(company_currency);
	},
	
	change_form_labels: function(company_currency) {
		var me = this;
		var field_label_map = {};
		
		var setup_field_label_map = function(fields_list, currency) {
			$.each(fields_list, function(i, fname) {
				var docfield = wn.meta.get_docfield(me.frm.doc.doctype, fname);
				if(docfield) {
					var label = wn._((docfield.label || "")).replace(/\([^\)]*\)/g, "");
					field_label_map[fname] = label.trim() + " (" + currency + ")";
				}
			});
		}
		
		setup_field_label_map(["net_total", "total_tax", "grand_total", "in_words",
			"other_charges_added", "other_charges_deducted", 
			"outstanding_amount", "total_advance", "total_amount_to_pay", "rounded_total"],
			company_currency);
		
		setup_field_label_map(["net_total_import", "grand_total_import", "in_words_import",
			"other_charges_added_import", "other_charges_deducted_import"], this.frm.doc.currency);
		
		setup_field_label_map(["conversion_rate"], 	"1 " + this.frm.doc.currency 
			+ " = [?] " + company_currency);
		
		if(this.frm.doc.price_list_currency && this.frm.doc.price_list_currency!=company_currency) {
			setup_field_label_map(["plc_conversion_rate"], 	"1 " + this.frm.doc.price_list_currency 
				+ " = [?] " + company_currency);
		}
		
		// toggle fields
		this.frm.toggle_display(["conversion_rate", "net_total", "grand_total", 
			"in_words", "other_charges_added", "other_charges_deducted"],
			this.frm.doc.currency != company_currency);
		
		// set labels
		$.each(field_label_map, function(fname, label) {
			me.frm.fields_dict[fname].set_label(label);
		});
	},
	
	change_grid_labels: function(company_currency) {
		var me = this;
		var field_label_map = {};
		
		var setup_field_label_map = function(fields_list, currency, parentfield) {
			var grid_doctype = me.frm.fields_dict[parentfield].grid.doctype;
			$.each(fields_list, function(i, fname) {
				var docfield = wn.meta.get_docfield(grid_doctype, fname);
				if(docfield) {
					field_label_map[grid_doctype + "-" + fname] = 
						docfield.label + " (" + currency + ")";
				}
			});
		}
		
		setup_field_label_map(["purchase_rate", "purchase_ref_rate", "amount", "rate"],
			company_currency, this.fname);
		
		setup_field_label_map(["import_rate", "import_ref_rate", "import_amount"],
			this.frm.doc.currency, this.fname);
		
		setup_field_label_map(["tax_amount", "total"], company_currency, this.other_fname);
		
		if(this.frm.fields_dict["advance_allocation_details"]) {
			setup_field_label_map(["advance_amount", "allocated_amount"], company_currency,
				"advance_allocation_details");
		}
		
		// toggle columns
		var item_grid = this.frm.fields_dict[this.fname].grid;
		var show = this.frm.doc.currency != company_currency;
		$.each(["purchase_rate", "purchase_ref_rate", "amount", "rate"], function(i, fname) {
			if(wn.meta.get_docfield(item_grid.doctype, fname))
				item_grid.set_column_disp(fname, show);
		});
		
		// set labels
		var $wrapper = $(this.frm.wrapper);
		$.each(field_label_map, function(fname, label) {
			$wrapper.find('[data-grid-fieldname="'+fname+'"]').text(label);
		});
	},
	
	get_company_currency: function() {
		return erpnext.get_currency(this.frm.doc.company);
	}
});

// to save previous state of cur_frm.cscript
var prev_cscript = {};
$.extend(prev_cscript, cur_frm.cscript);

cur_frm.cscript = new erpnext.buying.BuyingController({frm: cur_frm});

// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, prev_cscript);


var tname = cur_frm.cscript.tname;
var fname = cur_frm.cscript.fname;

cur_frm.cscript.get_default_schedule_date = function(doc) {
		var ch = getchildren( tname, doc.name, fname);
		if (flt(ch.length) > 0){
			$c_obj(make_doclist(doc.doctype, doc.name), 'get_default_schedule_date', '', function(r, rt) { refresh_field(fname); });
		}
}

cur_frm.cscript.load_taxes = function(doc, cdt, cdn, callback) {
	// run if this is not executed from dt_map...
	doc = locals[doc.doctype][doc.name];
	if(doc.supplier || getchildren('Purchase Taxes and Charges', doc.name, 'purchase_tax_details', doc.doctype).length) {
		if(callback) {
			callback(doc, cdt, cdn);
		}
	} else {
		$c_obj(make_doclist(doc.doctype, doc.name),'load_default_taxes','',function(r,rt){
			refresh_field('purchase_tax_details');
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

// ======================== Conversion Rate ==========================================
cur_frm.cscript.conversion_rate = function(doc,cdt,cdn) {
	cur_frm.cscript.calc_amount( doc, 1);
}

//==================== Item Code Get Query =======================================================
// Only Is Purchase Item = 'Yes' and Items not moved to trash are allowed.
cur_frm.fields_dict[fname].grid.get_field("item_code").get_query = function(doc, cdt, cdn) {
	if (doc.is_subcontracted =="Yes") {
		return erpnext.queries.item({
			'ifnull(tabItem.is_sub_contracted_item, "No")': 'Yes'
		})
	} else {
		return erpnext.queries.item({
			'ifnull(tabItem.is_purchase_item, "No")': 'Yes'
		})
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
cur_frm.cscript.uom = function(doc, cdt, cdn, args) {
	if(!args) args = {};
	
	// args passed can contain conversion_factor
	var d = locals[cdt][cdn];
	$.extend(args, {
		item_code: d.item_code,
		uom: d.uom,
		stock_qty: flt(d.stock_qty),
	});
	
	if(d.item_code && d.uom) {
		cur_frm.call({
			method: "buying.doctype.purchase_common.purchase_common.get_uom_details",
			args: { args: args },
			child: d,
			callback: function(r) {
				cur_frm.cscript.calc_amount(doc, 2);
			}
		});
	}
}


//==================== Conversion factor =========================================================
cur_frm.cscript.conversion_factor = function(doc, cdt, cdn) {
	var item = locals[cdt][cdn];
	
	cur_frm.cscript.uom(doc, cdt, cdn, { conversion_factor: item.conversion_factor });
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

//==================== Validate ====================================================================
cur_frm.cscript.validate = function(doc, cdt, cdn) {
	cur_frm.cscript.calc_amount(doc, 1);

	// calculate advances if pv
	if(doc.docstatus == 0 && doc.doctype == 'Purchase Invoice') calc_total_advance(doc, cdt, cdn);
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
		set_multiple(tname, cl[i].name, {
			'discount_rate': flt(cl[i].import_ref_rate) ? 
				flt(flt( flt( flt(cl[i].import_ref_rate) - flt(cl[i].import_rate) ) * 100 )/ 
					flt(cl[i].import_ref_rate))	: 0 }, fname);
		tmp[rate_fld] = flt(doc.conversion_rate) * flt(cl[i].import_rate);
			set_multiple(tname, cl[i].name, tmp, fname);

			set_multiple(tname, cl[i].name, {'amount': flt(flt(cl[i].qty) * flt(doc.conversion_rate) * flt(cl[i].import_rate))}, fname);
			set_multiple(tname, cl[i].name, {'import_amount': flt(flt(cl[i].qty) * flt(cl[i].import_rate))}, fname);

		}else if(n == 2){
		set_multiple(tname, cl[i].name, {'purchase_ref_rate':flt(cl[i].import_ref_rate)*flt(doc.conversion_rate)}, fname);
		set_multiple(tname, cl[i].name, {
			'discount_rate': flt(cl[i].purchase_ref_rate) ? 
				flt(flt( flt( flt(cl[i].purchase_ref_rate) - flt(cl[i][rate_fld]) ) * 100 )/
				flt(cl[i].purchase_ref_rate)) : 0 }, fname);
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
		
		var total = net_total;
		for(var t=0;t<tax.length;t++){
 
			var account = tax[t].account_head;
			$td(otc,0,t+1).innerHTML = account?account:'';
			//Check For Rate
			if(cl[i].item_tax_rate && check_tax[account]!=null)	{
				rate = flt(check_tax[account]);
			} else {
				// if particular item doesn't have particular rate it will take other charges rate
				rate = flt(tax[t].rate);
			}

			//Check For Rate and get tax amount
			var tax_amount = cur_frm.cscript.check_charge_type_and_get_tax_amount(doc,tax,t, cl[i], rate);
			
			//enter item_wise_tax_detail i.e. tax rate on each item
			
			item_wise_tax_detail = cur_frm.cscript.get_item_wise_tax_detail( doc, rate, cl, i, tax, t);
			
			
			if(tax[t].add_deduct_tax == 'Add'){
				// this is calculation part for all types
				if(tax[t].charge_type != "Actual") tax[t].item_wise_tax_detail += item_wise_tax_detail;
				tax[t].total_amount = flt(tax_amount);		 //stores actual tax amount in virtual field
				tax[t].total_tax_amount = flt(prev_total);			//stores total amount in virtual field
				tax[t].tax_amount += flt(tax_amount);			 
				var total_amount = flt(tax[t].tax_amount);
				total_tax_amount = flt(tax[t].total_tax_amount) + flt(total_amount);
				if(tax[t].category != "Valuation"){
					set_multiple('Purchase Taxes and Charges', tax[t].name, { 'item_wise_tax_detail':tax[t].item_wise_tax_detail, 'amount':roundNumber(total_amount, 2), 'total':roundNumber(flt(total)+flt(tax[t].tax_amount), 2)}, other_fname);
					prev_total += flt(tax[t].total_amount);
					total += flt(tax[t].tax_amount);	// for adding total to previous amount			 
				}
				else{
					set_multiple('Purchase Taxes and Charges', tax[t].name, { 'item_wise_tax_detail':tax[t].item_wise_tax_detail, 'amount':roundNumber(total_amount, 2), 'total':roundNumber(flt(total), 2)}, other_fname);
					prev_total = prev_total;
				}
				//prev_total += flt(tax[t].total_amount);	 // for previous row total

				if(tax[t].charge_type == 'Actual')
					$td(otc,i+1,t+1).innerHTML = format_currency(tax[t].total_amount, erpnext.get_currency(doc.company));
				else
					$td(otc,i+1,t+1).innerHTML = '('+fmt_money(rate) + '%) ' +format_currency(tax[t].total_amount, erpnext.get_currency(doc.company));

				if (tax[t].category != "Total"){
					item_tax += tax[t].total_amount;
				}
			}
			else if(tax[t].add_deduct_tax == 'Deduct'){
				// this is calculation part for all types
				if(tax[t].charge_type != "Actual") tax[t].item_wise_tax_detail += item_wise_tax_detail;
				tax[t].total_amount = flt(tax_amount);		 //stores actual tax amount in virtual field
				tax[t].total_tax_amount = flt(prev_total);			//stores total amount in virtual field
				tax[t].tax_amount += flt(tax_amount);
				var total_amount = flt(tax[t].tax_amount);
				total_tax_amount = flt(tax[t].total_tax_amount) - flt(total_amount);
				if(tax[t].category != "Valuation"){
					set_multiple('Purchase Taxes and Charges', tax[t].name, { 'item_wise_tax_detail':tax[t].item_wise_tax_detail, 'tax_amount':roundNumber(total_amount, 2), 'total':roundNumber(flt(total)-flt(tax[t].tax_amount), 2)}, other_fname);
					prev_total -= flt(tax[t].total_amount); 
					total -= flt(tax[t].tax_amount);	// for adding total to previous amount			 
				}
				else{
					set_multiple('Purchase Taxes and Charges', tax[t].name, { 'item_wise_tax_detail':tax[t].item_wise_tax_detail, 'tax_amount':roundNumber(total_amount, 2), 'total':roundNumber(flt(total), 2)}, other_fname);
					prev_total = prev_total;
				}
				//prev_total += flt(tax[t].total_amount);	 // for previous row total

				if(tax[t].charge_type == 'Actual')
					$td(otc,i+1,t+1).innerHTML = format_currency(tax[t].total_amount, erpnext.get_currency(doc.company));
				else
					$td(otc,i+1,t+1).innerHTML = '('+fmt_money(rate) + '%) ' +format_currency(tax[t].total_amount, erpnext.get_currency(doc.company));

				if (tax[t].category != "Total"){
					item_tax -= tax[t].total_amount;
				}
			}			
			
			
		}
		set_multiple(tname, cl[i].name, {'item_tax_amount': item_tax }, fname);
	}
	for(var t=0;t<tax.length;t++){
		tax[t].tax_amount = roundNumber(tax[t].tax_amount, 2);
	}
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
		if(d[j].category != 'Valuation'){
			
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

	doc.other_charges_added = roundNumber(flt(other_charges_added), 2);
	doc.other_charges_deducted = roundNumber(flt(other_charges_deducted), 2);
	doc.grand_total = roundNumber(flt(flt(net_total) + flt(other_charges_added) - flt(other_charges_deducted)), 2);
	doc.rounded_total = Math.round(doc.grand_total);
	doc.net_total_import = roundNumber(flt(flt(net_total) / flt(doc.conversion_rate)), 2);
	doc.other_charges_added_import = roundNumber(flt(flt(other_charges_added) / flt(doc.conversion_rate)), 2);
	doc.other_charges_deducted_import = roundNumber(flt(flt(other_charges_deducted) / flt(doc.conversion_rate)), 2);
	doc.grand_total_import = roundNumber(flt(flt(doc.grand_total) / flt(doc.conversion_rate)), 2);
	doc.rounded_total_import = Math.round(doc.grand_total_import);

	refresh_many(['net_total','total_taxes','grand_total']);


	if(doc.doctype == 'Purchase Invoice'){
		calculate_outstanding(doc);
	}
}

var calculate_outstanding = function(doc) {
	// total amount to pay	
	doc.total_amount_to_pay = flt(doc.grand_total) - flt(doc.write_off_amount);
	
	// outstanding amount 
	if(doc.docstatus==0) doc.outstanding_amount = doc.total_amount_to_pay - flt(doc.total_advance);
	
	refresh_many(['total_amount_to_pay', 'outstanding_amount']);
}


cur_frm.cscript.project_name = function(doc, cdt, cdn) {
	var item_doc = locals[cdt][cdn];
	if (item_doc.project_name) {
		$.each(getchildren(cur_frm.cscript.tname, doc.name, cur_frm.cscript.fname, doc.doctype),
			function(i, v) {
				if (v && !v.project_name) v.project_name = item_doc.project_name;
			});
		refresh_field(cur_frm.cscript.fname);
	}
}

cur_frm.fields_dict.supplier && (cur_frm.fields_dict.supplier.get_query = erpnext.utils.supplier_query);