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

cur_frm.cscript.tname = "Material Request Item";
cur_frm.cscript.fname = "indent_details";

wn.require('app/buying/doctype/purchase_common/purchase_common.js');
wn.require('app/utilities/doctype/sms_control/sms_control.js');

erpnext.buying.MaterialRequestController = erpnext.buying.BuyingController.extend({
	refresh: function(doc) {
		this._super();
		
		if(doc.docstatus == 1 && doc.status != 'Stopped'){
			if(doc.material_request_type === "Purchase")
				cur_frm.add_custom_button("Make Supplier Quotation", cur_frm.cscript.make_supplier_quotation);
				
			if(doc.material_request_type === "Transfer" && doc.status === "Submitted")
				cur_frm.add_custom_button("Transfer Material", cur_frm.cscript.make_stock_entry);
			
			if(flt(doc.per_ordered, 2) < 100) {
				if(doc.material_request_type === "Purchase")
					cur_frm.add_custom_button('Make Purchase Order', cur_frm.cscript['Make Purchase Order']);
				
				cur_frm.add_custom_button('Stop Material Request', cur_frm.cscript['Stop Material Request']);
			}
			cur_frm.add_custom_button('Send SMS', cur_frm.cscript.send_sms);

		}

		if(doc.docstatus == 1 && doc.status == 'Stopped')
			cur_frm.add_custom_button('Unstop Material Request', cur_frm.cscript['Unstop Material Request']);
		
		if(doc.material_request_type === "Transfer") {
			cur_frm.toggle_display("sales_order_no", false);
			cur_frm.fields_dict.indent_details.grid.set_column_disp("sales_order_no", false);
		}
	}
});

var new_cscript = new erpnext.buying.MaterialRequestController({frm: cur_frm});

// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, new_cscript);

	
cur_frm.cscript.onload = function(doc, cdt, cdn) {
	if (!doc.transaction_date) doc.transaction_date = dateutil.obj_to_str(new Date());
	if (!doc.status) doc.status = 'Draft';

	// defined in purchase_common.js
	//cur_frm.cscript.update_item_details(doc, cdt, cdn);
};

cur_frm.cscript.onload_post_render = function(doc, cdt, cdn) {
	// second call
	if(doc.__islocal){ 
		cur_frm.cscript.get_item_defaults(doc);
	}	
};

cur_frm.cscript.get_item_defaults = function(doc) {
		var ch = getchildren( 'Material Request Item', doc.name, 'indent_details');
		if (flt(ch.length) > 0){
			$c_obj(make_doclist(doc.doctype, doc.name), 'get_item_defaults', '', function(r, rt) {refresh_field('indent_details'); });
		}
};

cur_frm.cscript.transaction_date = function(doc,cdt,cdn){
	if(doc.__islocal){ 
		cur_frm.cscript.get_default_schedule_date(doc);
	}
};

cur_frm.cscript.qty = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	if (flt(d.qty) < flt(d.min_order_qty))
		alert("Warning: Material Requested Qty is less than Minimum Order Qty");
};

cur_frm.cscript['Stop Material Request'] = function() {
	var doc = cur_frm.doc;
	var check = confirm("Do you really want to STOP this Material Request?");

	if (check) {
		$c('runserverobj', args={'method':'update_status', 'arg': 'Stopped', 'docs': wn.model.compress(make_doclist(doc.doctype, doc.name))}, function(r,rt) {
			cur_frm.refresh();
		});
	}
};

cur_frm.cscript['Unstop Material Request'] = function(){
	var doc = cur_frm.doc;
	var check = confirm("Do you really want to UNSTOP this Material Request?");
	
	if (check) {
		$c('runserverobj', args={'method':'update_status', 'arg': 'Submitted','docs': wn.model.compress(make_doclist(doc.doctype, doc.name))}, function(r,rt) {
			cur_frm.refresh();
			
		});
	}
};

cur_frm.cscript['Make Purchase Order'] = function() {
	cur_frm.map([["Material Request", "Purchase Order"], ["Material Request Item", "Purchase Order Item"]]);
};

cur_frm.cscript.make_supplier_quotation = function() {
	cur_frm.map([["Material Request", "Supplier Quotation"], ["Material Request Item", "Supplier Quotation Item"]]);
};

cur_frm.cscript.make_stock_entry = function() {
	cur_frm.map([["Material Request", "Stock Entry"], ["Material Request Item", "Stock Entry Detail"]]);
};
