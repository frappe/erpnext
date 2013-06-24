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

cur_frm.cscript.tname = "Purchase Receipt Item";
cur_frm.cscript.fname = "purchase_receipt_details";
cur_frm.cscript.other_fname = "purchase_tax_details";

wn.require('app/accounts/doctype/purchase_taxes_and_charges_master/purchase_taxes_and_charges_master.js');
wn.require('app/buying/doctype/purchase_common/purchase_common.js');
wn.require('app/utilities/doctype/sms_control/sms_control.js');

erpnext.buying.PurchaseReceiptController = erpnext.buying.BuyingController.extend({
	refresh: function() {
		this._super();
		
		if(this.frm.doc.docstatus == 1) {
			if(flt(this.frm.doc.per_billed, 2) < 100) {
				cur_frm.add_custom_button('Make Purchase Invoice', 
					cur_frm.cscript['Make Purchase Invoice']);
			}
			cur_frm.add_custom_button('Send SMS', cur_frm.cscript['Send SMS']);
		}

		if(wn.boot.control_panel.country == 'India') {
			unhide_field(['challan_no', 'challan_date']);
		}
	}, 
	onload_post_render: function(doc, dt, dn) {	
		var me = this;
		var callback = function(doc, dt, dn) {
			me.update_item_details(doc, dt, dn, function(r,rt) { });
		}
		
		// TODO: improve this
		if(this.frm.doc.__islocal) {
			if (this.frm.fields_dict.price_list_name && this.frm.doc.price_list_name) 
				this.price_list_name(callback);
			else
				callback(doc, dt, dn);
		}
	}
});

var new_cscript = new erpnext.buying.PurchaseReceiptController({frm: cur_frm});

// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, new_cscript);

cur_frm.cscript.onload = function(doc, cdt, cdn) {
	if(!doc.fiscal_year && doc.__islocal){ wn.model.set_default_values(doc);}
	if (!doc.posting_date) doc.posting_date = dateutil.obj_to_str(new Date());
	if (!doc.transaction_date) doc.transaction_date = dateutil.obj_to_str(new Date());
	if (!doc.status) doc.status = 'Draft';
}

cur_frm.cscript.supplier = function(doc,dt,dn) {
	if (doc.supplier) {
		get_server_fields('get_default_supplier_address',
			JSON.stringify({ supplier: doc.supplier }),'', doc, dt, dn, 1, function() {
				cur_frm.refresh();
			});
	}
}

cur_frm.cscript.supplier_address = cur_frm.cscript.contact_person = function(doc,dt,dn) {		
	if(doc.supplier) get_server_fields('get_supplier_address', JSON.stringify({supplier: doc.supplier, address: doc.supplier_address, contact: doc.contact_person}),'', doc, dt, dn, 1);
}

cur_frm.fields_dict['supplier_address'].get_query = function(doc, cdt, cdn) {
	return 'SELECT name,address_line1,city FROM tabAddress WHERE supplier = "'+ doc.supplier +'" AND docstatus != 2 AND name LIKE "%s" ORDER BY name ASC LIMIT 50';
}

cur_frm.fields_dict['contact_person'].get_query = function(doc, cdt, cdn) {
	return 'SELECT name,CONCAT(first_name," ",ifnull(last_name,"")) As FullName,department,designation FROM tabContact WHERE supplier = "'+ doc.supplier +'" AND docstatus != 2 AND name LIKE "%s" ORDER BY name ASC LIMIT 50';
}


cur_frm.fields_dict.supplier_address.on_new = function(dn) {
	locals['Address'][dn].supplier = locals[cur_frm.doctype][cur_frm.docname].supplier;
	locals['Address'][dn].supplier_name = locals[cur_frm.doctype][cur_frm.docname].supplier_name;
}

cur_frm.fields_dict.contact_person.on_new = function(dn) {
	locals['Contact'][dn].supplier = locals[cur_frm.doctype][cur_frm.docname].supplier;
	locals['Contact'][dn].supplier_name = locals[cur_frm.doctype][cur_frm.docname].supplier_name;
}


// Get Purchase Order Button
// -----------------
cur_frm.cscript.pull_purchase_order_details = function(doc, dt, dn) {
	$c_obj(make_doclist(dt,dn),'get_po_details','',function(r,rt) { 
		cur_frm.refresh_fields();
	});
}



//================ create new contact ============================================================================
cur_frm.cscript.new_contact = function(){
	tn = wn.model.make_new_doc_and_get_name('Contact');
	locals['Contact'][tn].is_supplier = 1;
	if(doc.supplier) locals['Contact'][tn].supplier = doc.supplier;
	loaddoc('Contact', tn);
}

// ***************** Get project name *****************
cur_frm.fields_dict['purchase_receipt_details'].grid.get_field('project_name').get_query = function(doc, cdt, cdn) {
	return 'SELECT `tabProject`.name FROM `tabProject` \
		WHERE `tabProject`.status not in ("Completed", "Cancelled") \
		AND `tabProject`.name LIKE "%s" ORDER BY `tabProject`.name ASC LIMIT 50';
}


//========================= Overloaded query for link batch_no =============================================================
cur_frm.fields_dict['purchase_receipt_details'].grid.get_field('batch_no').get_query= function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	if(d.item_code){
		return "SELECT tabBatch.name, tabBatch.description FROM tabBatch WHERE tabBatch.docstatus != 2 AND tabBatch.item = '"+ d.item_code +"' AND `tabBatch`.`name` like '%s' ORDER BY `tabBatch`.`name` DESC LIMIT 50"
	}
	else{
		alert("Please enter Item Code.");
	}
}

cur_frm.cscript.select_print_heading = function(doc,cdt,cdn){
	if(doc.select_print_heading){
		// print heading
		cur_frm.pformat.print_heading = doc.select_print_heading;
	}
	else
		cur_frm.pformat.print_heading = "Purchase Receipt";
}
// ***************** Get Print Heading	*****************
cur_frm.fields_dict['select_print_heading'].get_query = function(doc, cdt, cdn) {
	return 'SELECT `tabPrint Heading`.name FROM `tabPrint Heading` WHERE `tabPrint Heading`.docstatus !=2 AND `tabPrint Heading`.name LIKE "%s" ORDER BY `tabPrint Heading`.name ASC LIMIT 50';
}

//========================= Received Qty =============================================================

cur_frm.cscript.received_qty = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	ret = {
			'qty' : (flt(d.qty) && flt(d.qty) < flt(d.received_qty)) 
			 	? flt(d.qty) : flt(d.received_qty),
			'stock_qty': 0,
			'rejected_qty' : 0,
		}
	set_multiple('Purchase Receipt Item', cdn, ret, 'purchase_receipt_details');
	cur_frm.cscript.calc_amount(doc, 2);
}

//======================== Qty (Accepted Qty) =========================================================

cur_frm.cscript.qty = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	// Step 1 :=> Check If Qty > Received Qty
	if (flt(d.qty) > flt(d.received_qty)) {
		alert("Accepted Qty cannot be greater than Received Qty")
		ret = {
			'qty' : 0,
			'stock_qty': 0,
			'rejected_qty' : 0
		}
		// => Set Qty = 0 and rejected_qty = 0
		set_multiple('Purchase Receipt Item', cdn, ret, 'purchase_receipt_details');
		cur_frm.cscript.calc_amount(doc, 2);
		// => Return
		return
	}
	// Step 2 :=> Check IF Qty <= REceived Qty
	else {
		ret = {
			'rejected_qty':flt(d.received_qty) - flt(d.qty)
		}
		// => Set Rejected Qty = Received Qty - Qty
		set_multiple('Purchase Receipt Item', cdn, ret, 'purchase_receipt_details');
		// => Calculate Amount
		cur_frm.cscript.calc_amount(doc, 2);
		cur_frm.cscript.update_stock_qty(doc,cdt,cdn);
	}	
}

//======================== Rejected Qty =========================================================
cur_frm.cscript.rejected_qty = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	// Step 1 :=> Check If Rejected Qty > Received Qty
	if (flt(d.rejected_qty) > flt(d.received_qty)) {
		alert("Rejected Qty cannot be greater than Received Qty") 
		ret = {
			'qty' : 0,
			'stock_qty': 0,
			'rejected_qty' : 0
		}
		// => Set Qty = 0 and rejected_qty = 0
		set_multiple('Purchase Receipt Item', cdn, ret, 'purchase_receipt_details');
		cur_frm.cscript.calc_amount(doc, 2);
		// => Return
		return
	}
	// Step 2 :=> Check IF Rejected Qty <= REceived Qty
	else {
		ret = {
			'qty':flt(d.received_qty) - flt(d.rejected_qty)
		}
		// => Set Qty = Received Qty - Rejected Qty
		set_multiple('Purchase Receipt Item', cdn, ret, 'purchase_receipt_details');
		// Calculate Amount
		cur_frm.cscript.calc_amount(doc, 2);
		cur_frm.cscript.update_stock_qty(doc,cdt,cdn);
	}
}

//================================= Purchase Order No Get Query ====================================
cur_frm.fields_dict['purchase_order_no'].get_query = function(doc) {
	if (doc.supplier)
		return 'SELECT DISTINCT `tabPurchase Order`.`name` FROM `tabPurchase Order` WHERE `tabPurchase Order`.`supplier` = "' +doc.supplier + '" and`tabPurchase Order`.`docstatus` = 1 and `tabPurchase Order`.`status` != "Stopped" and ifnull(`tabPurchase Order`.`per_received`, 0) < 99.99	and `tabPurchase Order`.`currency` = ifnull("' +doc.currency+ '","") and `tabPurchase Order`.company = "'+ doc.company +'" and `tabPurchase Order`.%(key)s LIKE "%s" ORDER BY `tabPurchase Order`.`name` DESC LIMIT 50';
	else
		return 'SELECT DISTINCT `tabPurchase Order`.`name` FROM `tabPurchase Order` WHERE `tabPurchase Order`.`docstatus` = 1 and `tabPurchase Order`.`company` = "'+ doc.company +'" and `tabPurchase Order`.`status` != "Stopped" and ifnull(`tabPurchase Order`.`per_received`, 0) < 99.99 and `tabPurchase Order`.%(key)s LIKE "%s" ORDER BY `tabPurchase Order`.`name` DESC LIMIT 50';
}

// QA INspection report get_query
//---------------------------------

cur_frm.fields_dict.purchase_receipt_details.grid.get_field("qa_no").get_query = function(doc) {
	return 'SELECT `tabQuality Inspection`.name FROM `tabQuality Inspection` WHERE `tabQuality Inspection`.docstatus = 1 AND `tabQuality Inspection`.%(key)s LIKE "%s"';
}

// On Button Click Functions
// ------------------------------------------------------------------------------


// ================================ Make Purchase Invoice ==========================================
cur_frm.cscript['Make Purchase Invoice'] = function() {
	n = wn.model.make_new_doc_and_get_name('Purchase Invoice');
	$c('dt_map', args={
		'docs':wn.model.compress([locals['Purchase Invoice'][n]]),
		'from_doctype': cur_frm.doc.doctype,
		'to_doctype':'Purchase Invoice',
		'from_docname': cur_frm.doc.name,
		'from_to_list':"[['Purchase Receipt','Purchase Invoice'],['Purchase Receipt Item','Purchase Invoice Item'],['Purchase Taxes and Charges','Purchase Taxes and Charges']]"
		}, function(r,rt) {
			loaddoc('Purchase Invoice', n);
		}
	);
}




//****************** For print sales order no and date*************************
cur_frm.pformat.purchase_order_no = function(doc, cdt, cdn){
	//function to make row of table
	
	var make_row = function(title,val1, val2, bold){
		var bstart = '<b>'; var bend = '</b>';

		return '<tr><td style="width:39%;">'+(bold?bstart:'')+title+(bold?bend:'')+'</td>'
		 +'<td style="width:61%;text-align:left;">'+val1+(val2?' ('+dateutil.str_to_user(val2)+')':'')+'</td>'
		 +'</tr>'
	}

	out ='';
	
	var cl = getchildren('Purchase Receipt Item',doc.name,'purchase_receipt_details');

	// outer table	
	var out='<div><table class="noborder" style="width:100%"><tr><td style="width: 50%"></td><td>';
	
	// main table
	out +='<table class="noborder" style="width:100%">';

	// add rows
	if(cl.length){
		prevdoc_list = new Array();
		for(var i=0;i<cl.length;i++){
			if(cl[i].prevdoc_doctype == 'Purchase Order' && cl[i].prevdoc_docname && prevdoc_list.indexOf(cl[i].prevdoc_docname) == -1) {
				prevdoc_list.push(cl[i].prevdoc_docname);
				if(prevdoc_list.length ==1)
					out += make_row(cl[i].prevdoc_doctype, cl[i].prevdoc_docname, cl[i].prevdoc_date,0);
				else
					out += make_row('', cl[i].prevdoc_docname, cl[i].prevdoc_date,0);
			}
		}
	}

	out +='</table></td></tr></table></div>';

	return out;
}

cur_frm.cscript.on_submit = function(doc, cdt, cdn) {
	if(cint(wn.boot.notification_settings.purchase_receipt)) {
		cur_frm.email_doc(wn.boot.notification_settings.purchase_receipt_message);
	}
}
