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

cur_frm.cscript.tname = "Purchase Request Item";
cur_frm.cscript.fname = "indent_details";

wn.require('erpnext/buying/doctype/purchase_common/purchase_common.js');
wn.require('erpnext/utilities/doctype/sms_control/sms_control.js');
cur_frm.cscript.indent_doctype_label =	get_doctype_label('Purchase Request');
	
//========================== On Load =================================================
cur_frm.cscript.onload = function(doc, cdt, cdn) {
	if (!doc.transaction_date) doc.transaction_date = dateutil.obj_to_str(new Date())
	if (!doc.status) doc.status = 'Draft';

	// defined in purchase_common.js
	//cur_frm.cscript.update_item_details(doc, cdt, cdn);
}

cur_frm.cscript.onload_post_render = function(doc, cdt, cdn) {
	// second call
	if(doc.__islocal){ 
		cur_frm.cscript.get_item_defaults(doc);
	}	
}

cur_frm.cscript.get_item_defaults = function(doc) {
		var ch = getchildren( 'Purchase Request Item', doc.name, 'indent_details');
		if (flt(ch.length) > 0){
			$c_obj(make_doclist(doc.doctype, doc.name), 'get_item_defaults', '', function(r, rt) {refresh_field('indent_details'); });
		}
}


//======================= Refresh =====================================
cur_frm.cscript.refresh = function(doc, cdt, cdn) { 

	// Unhide Fields in Next Steps
	// ---------------------------------
	
	cur_frm.clear_custom_buttons();

	if(doc.docstatus == 1 && doc.status != 'Stopped'){
		var ch = getchildren('Purchase Request Item',doc.name,'indent_details');
		var is_closed = 1;
		for(var i in ch){
			if(flt(ch[i].qty) > flt(ch[i].ordered_qty)) is_closed = 0;
		}
		if(!is_closed) {
			cur_frm.add_custom_button('Make Purchase Order', cur_frm.cscript['Make Purchase Order'])
			cur_frm.add_custom_button('Stop ' + cur_frm.cscript.indent_doctype_label, cur_frm.cscript['Stop Purchase Requisition'])
		}
		cur_frm.add_custom_button('Send SMS', cur_frm.cscript['Send SMS']);
	}
 
	if(doc.docstatus == 1 && doc.status == 'Stopped')
		cur_frm.add_custom_button('Unstop ' + cur_frm.cscript.indent_doctype_label, cur_frm.cscript['Unstop Purchase Requisition'])
		
	if(doc.docstatus == 1)
		unhide_field(['Repair Purchase Requisition']);
	else
		hide_field(['Repair Purchase Requisition']);
}

//======================= validation ===================================
cur_frm.cscript.validate = function(doc,cdt,cdn){
	is_item_table(doc,cdt,cdn);
}
//======================= transaction date =============================
cur_frm.cscript.transaction_date = function(doc,cdt,cdn){
	if(doc.__islocal){ 
		cur_frm.cscript.get_default_schedule_date(doc);
	}
}

//=================== Quantity ===================================================================
cur_frm.cscript.qty = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	if (flt(d.qty) < flt(d.min_order_qty))
		alert("Warning: " + cur_frm.cscript.indent_doctype_label + " Qty is less than Minimum Order Qty");
}

// On Button Click Functions
// ------------------------------------------------------------------------------

// Make Purchase Order
cur_frm.cscript['Make Purchase Order'] = function() {
	var doc = cur_frm.doc;
	n = createLocal('Purchase Order');
	$c('dt_map', args={
		'docs':compress_doclist([locals['Purchase Order'][n]]),
		'from_doctype':doc.doctype,
		'to_doctype':'Purchase Order',
		'from_docname':doc.name,
		'from_to_list':"[['Purchase Request','Purchase Order'],['Purchase Request Item','Purchase Order Item']]"
		}, function(r,rt) {
			 loaddoc('Purchase Order', n);
		}
	);
}

// Stop INDENT
// ==================================================================================================
cur_frm.cscript['Stop Purchase Requisition'] = function() {
	var doc = cur_frm.doc;
	var check = confirm("Do you really want to STOP this " + cur_frm.cscript.indent_doctype_label + "?");

	if (check) {
		$c('runserverobj', args={'method':'update_status', 'arg': 'Stopped', 'docs': compress_doclist(make_doclist(doc.doctype, doc.name))}, function(r,rt) {
			cur_frm.refresh();
		});
	}
}

// Un Stop INDENT
//====================================================================================================
cur_frm.cscript['Unstop Purchase Requisition'] = function(){
	var doc = cur_frm.doc
	var check = confirm("Do you really want to UNSTOP this " + cur_frm.cscript.indent_doctype_label + "?");
	
	if (check) {
		$c('runserverobj', args={'method':'update_status', 'arg': 'Submitted','docs': compress_doclist(make_doclist(doc.doctype, doc.name))}, function(r,rt) {
			cur_frm.refresh();
			
		});
	}
}
