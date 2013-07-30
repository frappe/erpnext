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

wn.provide("erpnext.buying");

cur_frm.cscript.tname = "Purchase Order Item";
cur_frm.cscript.fname = "po_details";
cur_frm.cscript.other_fname = "purchase_tax_details";

wn.require('app/accounts/doctype/purchase_taxes_and_charges_master/purchase_taxes_and_charges_master.js');
wn.require('app/utilities/doctype/sms_control/sms_control.js');
wn.require('app/buying/doctype/purchase_common/purchase_common.js');

erpnext.buying.PurchaseOrderController = erpnext.buying.BuyingController.extend({
	refresh: function(doc, cdt, cdn) {
		this._super();
		this.frm.dashboard.reset();
		
		if(doc.docstatus == 1 && doc.status != 'Stopped'){
			cur_frm.dashboard.add_progress(cint(doc.per_received) + wn._("% Received"), 
				doc.per_received);
			cur_frm.dashboard.add_progress(cint(doc.per_billed) + wn._("% Billed"), 
				doc.per_billed);


			cur_frm.add_custom_button('Send SMS', cur_frm.cscript['Send SMS']);
			if(flt(doc.per_received, 2) < 100) 
				cur_frm.add_custom_button('Make Purchase Receipt', this.make_purchase_receipt);	
			if(flt(doc.per_billed, 2) < 100) 
				cur_frm.add_custom_button('Make Invoice', this.make_purchase_invoice);
			if(flt(doc.per_billed, 2) < 100 || doc.per_received < 100) 
				cur_frm.add_custom_button('Stop', cur_frm.cscript['Stop Purchase Order']);
		} else if(doc.docstatus===0) {
			cur_frm.cscript.add_from_mappers();
		}

		if(doc.docstatus == 1 && doc.status == 'Stopped')
			cur_frm.add_custom_button('Unstop Purchase Order', 
				cur_frm.cscript['Unstop Purchase Order']);
	},
		
	make_purchase_receipt: function() {
		wn.model.open_mapped_doc({
			method: "buying.doctype.purchase_order.purchase_order.make_purchase_receipt",
			source_name: cur_frm.doc.name
		})
	},
	
	make_purchase_invoice: function() {
		wn.model.open_mapped_doc({
			method: "buying.doctype.purchase_order.purchase_order.make_purchase_invoice",
			source_name: cur_frm.doc.name
		})
	},
	
	add_from_mappers: function() {
		cur_frm.add_custom_button(wn._('From Material Request'), 
			function() {
				wn.model.map_current_doc({
					method: "stock.doctype.material_request.material_request.make_purchase_order",
					source_doctype: "Material Request",
					get_query_filters: {
						material_request_type: "Purchase",
						docstatus: 1,
						status: ["!=", "Stopped"],
						per_ordered: ["<", 99.99],
						company: cur_frm.doc.company
					}
				})
			}
		);

		cur_frm.add_custom_button(wn._('From Supplier Quotation'), 
			function() {
				wn.model.map_current_doc({
					method: "buying.doctype.supplier_quotation.supplier_quotation.make_purchase_order",
					source_doctype: "Supplier Quotation",
					get_query_filters: {
						docstatus: 1,
						status: ["!=", "Stopped"],
						company: cur_frm.doc.company
					}
				})
			}
		);	
			
		cur_frm.add_custom_button(wn._('For Supplier'), 
			function() {
				wn.model.map_current_doc({
					method: "stock.doctype.material_request.material_request.make_purchase_order_based_on_supplier",
					source_doctype: "Supplier",
					get_query_filters: {
						docstatus: ["!=", 2],
					}
				})
			}
		);
	},

	tc_name: function() {
		this.get_terms();
	},

});

// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, new erpnext.buying.PurchaseOrderController({frm: cur_frm}));

cur_frm.fields_dict['supplier_address'].get_query = function(doc, cdt, cdn) {
	return {
		filters: {'supplier': doc.supplier}
	}
}

cur_frm.fields_dict['contact_person'].get_query = function(doc, cdt, cdn) {
	return {
		filters: {'supplier': doc.supplier}
	}
}

cur_frm.fields_dict['po_details'].grid.get_field('project_name').get_query = function(doc, cdt, cdn) {
	return {
		filters:[
			['Project', 'status', 'not in', 'Completed, Cancelled']
		]
	}
}

cur_frm.cscript.get_last_purchase_rate = function(doc, cdt, cdn){
	return $c_obj(make_doclist(doc.doctype, doc.name), 'get_last_purchase_rate', '', function(r, rt) { 
		refresh_field(cur_frm.cscript.fname);
		var doc = locals[cdt][cdn];
		cur_frm.cscript.calc_amount( doc, 2);
	});
}

cur_frm.cscript['Stop Purchase Order'] = function() {
	var doc = cur_frm.doc;
	var check = confirm("Do you really want to STOP " + doc.name);

	if (check) {
		return $c('runserverobj', args={'method':'update_status', 'arg': 'Stopped', 'docs': wn.model.compress(make_doclist(doc.doctype, doc.name))}, function(r,rt) {
			cur_frm.refresh();
		});	
	}
}

cur_frm.cscript['Unstop Purchase Order'] = function() {
	var doc = cur_frm.doc;
	var check = confirm("Do you really want to UNSTOP " + doc.name);

	if (check) {
		return $c('runserverobj', args={'method':'update_status', 'arg': 'Submitted', 'docs': wn.model.compress(make_doclist(doc.doctype, doc.name))}, function(r,rt) {
			cur_frm.refresh();
		});	
	}
}

cur_frm.pformat.indent_no = function(doc, cdt, cdn){
	//function to make row of table
	
	var make_row = function(title,val1, val2, bold){
		var bstart = '<b>'; var bend = '</b>';

		return '<tr><td style="width:39%;">'+(bold?bstart:'')+title+(bold?bend:'')+'</td>'
		 +'<td style="width:61%;text-align:left;">'+val1+(val2?' ('+dateutil.str_to_user(val2)+')':'')+'</td>'
		 +'</tr>'
	}

	out ='';
	
	var cl = getchildren('Purchase Order Item',doc.name,'po_details');

	// outer table	
	var out='<div><table class="noborder" style="width:100%"><tr><td style="width: 50%"></td><td>';
	
	// main table
	out +='<table class="noborder" style="width:100%">';

	// add rows
	if(cl.length){
		prevdoc_list = new Array();
		for(var i=0;i<cl.length;i++){
			if(cl[i].prevdoc_doctype == 'Material Request' && cl[i].prevdoc_docname && prevdoc_list.indexOf(cl[i].prevdoc_docname) == -1) {
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
	if(cint(wn.boot.notification_settings.purchase_order)) {
		cur_frm.email_doc(wn.boot.notification_settings.purchase_order_message);
	}
}
