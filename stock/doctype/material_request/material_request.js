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

wn.require('app/utilities/doctype/sms_control/sms_control.js');
wn.require('app/buying/doctype/purchase_common/purchase_common.js');

erpnext.buying.MaterialRequestController = erpnext.buying.BuyingController.extend({
	refresh: function(doc) {
		this._super();
		
		// dashboard
		cur_frm.dashboard.reset();
		if(doc.docstatus===1) {
			if(doc.status==="Stopped") {
				cur_frm.dashboard.set_headline_alert(wn._("Stopped"), "alert-danger", "icon-stop")
			}
			cur_frm.dashboard.add_progress(cint(doc.per_ordered) + "% " 
				+ wn._("Fulfilled"), cint(doc.per_ordered));
		}
		
		if(doc.docstatus == 1 && doc.status != 'Stopped'){
			if(doc.material_request_type === "Purchase")
				cur_frm.add_custom_button("Make Supplier Quotation", 
					this.make_supplier_quotation);
				
			if(doc.material_request_type === "Transfer" && doc.status === "Submitted")
				cur_frm.add_custom_button("Transfer Material", this.make_stock_entry);
			
			if(flt(doc.per_ordered, 2) < 100) {
				if(doc.material_request_type === "Purchase")
					cur_frm.add_custom_button('Make Purchase Order', 
						this.make_purchase_order);
				
				cur_frm.add_custom_button('Stop Material Request', 
					cur_frm.cscript['Stop Material Request']);
			}
			cur_frm.add_custom_button('Send SMS', cur_frm.cscript.send_sms);

		}

		if(doc.docstatus == 1 && doc.status == 'Stopped')
			cur_frm.add_custom_button('Unstop Material Request', 
				cur_frm.cscript['Unstop Material Request']);
		
		if(doc.material_request_type === "Transfer") {
			cur_frm.toggle_display("sales_order_no", false);
			cur_frm.fields_dict.indent_details.grid.set_column_disp("sales_order_no", false);
		}
	},
	
	validate_company_and_party: function(party_field) {
		return true;
	},
	
	calculate_taxes_and_totals: function() {
		return;
	},
	
	pull_sales_order_details: function(doc) {
		wn.model.map_current_doc({
			method: "selling.doctype.sales_order.sales_order.make_material_request",
			source_name: cur_frm.doc.sales_order_no,
		});
	},
	
	make_purchase_order: function() {
		wn.model.open_mapped_doc({
			method: "stock.doctype.material_request.material_request.make_purchase_order",
			source_name: cur_frm.doc.name
		})
	},

	make_supplier_quotation: function() {
		wn.model.open_mapped_doc({
			method: "stock.doctype.material_request.material_request.make_supplier_quotation",
			source_name: cur_frm.doc.name
		})
	},

	make_stock_entry: function() {
		wn.model.open_mapped_doc({
			method: "stock.doctype.material_request.material_request.make_stock_entry",
			source_name: cur_frm.doc.name
		})
	}
});

// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, new erpnext.buying.MaterialRequestController({frm: cur_frm}));
	
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
