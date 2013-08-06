// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
// License: GNU General Public License v3. See license.txt

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
		
		if (this.frm.doc.docstatus===0) {
			cur_frm.add_custom_button(wn._('From Sales Order'), 
				function() {
					wn.model.map_current_doc({
						method: "selling.doctype.sales_order.sales_order.make_material_request",
						source_doctype: "Sales Order",
						get_query_filters: {
							docstatus: 1,
							status: ["!=", "Stopped"],
							per_delivered: ["<", 99.99],
							company: cur_frm.doc.company
						}
					})
				});
		}

		if(doc.docstatus == 1 && doc.status == 'Stopped')
			cur_frm.add_custom_button('Unstop Material Request', 
				cur_frm.cscript['Unstop Material Request']);
		
	},
	
	tc_name: function() {
		this.get_terms();
	},
	
	validate_company_and_party: function(party_field) {
		return true;
	},
	
	calculate_taxes_and_totals: function() {
		return;
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
		return $c('runserverobj', args={'method':'update_status', 'arg': 'Stopped', 'docs': wn.model.compress(make_doclist(doc.doctype, doc.name))}, function(r,rt) {
			cur_frm.refresh();
		});
	}
};

cur_frm.cscript['Unstop Material Request'] = function(){
	var doc = cur_frm.doc;
	var check = confirm("Do you really want to UNSTOP this Material Request?");
	
	if (check) {
		return $c('runserverobj', args={'method':'update_status', 'arg': 'Submitted','docs': wn.model.compress(make_doclist(doc.doctype, doc.name))}, function(r,rt) {
			cur_frm.refresh();
		});
	}
};
