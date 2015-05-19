// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.buying");

{% include 'buying/doctype/purchase_common/purchase_common.js' %};

erpnext.buying.PurchaseOrderController = erpnext.buying.BuyingController.extend({
	refresh: function(doc, cdt, cdn) {
		var me = this;
		this._super();
		// this.frm.dashboard.reset();

		if(doc.docstatus == 1 && doc.status != 'Stopped'){
			// cur_frm.dashboard.add_progress(cint(doc.per_received) + __("% Received"),
			// 	doc.per_received);
			// cur_frm.dashboard.add_progress(cint(doc.per_billed) + __("% Billed"),
			// 	doc.per_billed);

			if(flt(doc.per_received, 2) < 100) {
				cur_frm.add_custom_button(__('Make Purchase Receipt'),
					this.make_purchase_receipt);
				if(doc.is_subcontracted==="Yes") {
					cur_frm.add_custom_button(__('Transfer Material to Supplier'),
						function() { me.make_stock_entry() });
				}
			}
			if(flt(doc.per_billed, 2) < 100)
				cur_frm.add_custom_button(__('Make Invoice'), this.make_purchase_invoice,
					frappe.boot.doctype_icons["Purchase Invoice"]);
			if(flt(doc.per_billed, 2) < 100 || doc.per_received < 100)
				cur_frm.add_custom_button(__('Stop'), cur_frm.cscript['Stop Purchase Order'],
					"icon-exclamation", "btn-default");

		} else if(doc.docstatus===0) {
			cur_frm.cscript.add_from_mappers();
		}

		if(doc.docstatus == 1 && doc.status == 'Stopped')
			cur_frm.add_custom_button(__('Unstop Purchase Order'),
				cur_frm.cscript['Unstop Purchase Order'], "icon-check");
	},

	make_stock_entry: function() {
		var items = $.map(cur_frm.doc.items, function(d) { return d.bom ? d.item_code : false; }),
			me = this;
		if(items.length===1) {
			me._make_stock_entry(items[0]);
			return;
		}
		frappe.prompt({fieldname:"item", options: items, fieldtype:"Select",
			label: __("Select Item for Transfer"), reqd: 1}, function(data) {
			me._make_stock_entry(data.item);
		}, __("Select Item"), __("Make"));
	},

	_make_stock_entry: function(item) {
		frappe.call({
			method:"erpnext.buying.doctype.purchase_order.purchase_order.make_stock_entry",
			args: {
				purchase_order: cur_frm.doc.name,
				item_code: item
			},
			callback: function(r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	},

	make_purchase_receipt: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_receipt",
			frm: cur_frm
		})
	},

	make_purchase_invoice: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_invoice",
			frm: cur_frm
		})
	},

	add_from_mappers: function() {
		cur_frm.add_custom_button(__('From Material Request'),
			function() {
				frappe.model.map_current_doc({
					method: "erpnext.stock.doctype.material_request.material_request.make_purchase_order",
					source_doctype: "Material Request",
					get_query_filters: {
						material_request_type: "Purchase",
						docstatus: 1,
						status: ["!=", "Stopped"],
						per_ordered: ["<", 99.99],
						company: cur_frm.doc.company
					}
				})
			}, "icon-download", "btn-default"
		);

		cur_frm.add_custom_button(__('From Supplier Quotation'),
			function() {
				frappe.model.map_current_doc({
					method: "erpnext.buying.doctype.supplier_quotation.supplier_quotation.make_purchase_order",
					source_doctype: "Supplier Quotation",
					get_query_filters: {
						docstatus: 1,
						status: ["!=", "Stopped"],
						company: cur_frm.doc.company
					}
				})
			}, "icon-download", "btn-default"
		);

		cur_frm.add_custom_button(__('For Supplier'),
			function() {
				frappe.model.map_current_doc({
					method: "erpnext.stock.doctype.material_request.material_request.make_purchase_order_based_on_supplier",
					source_doctype: "Supplier",
					get_query_filters: {
						docstatus: ["!=", 2],
					}
				})
			}, "icon-download", "btn-default"
		);
	},

	tc_name: function() {
		this.get_terms();
	},

	items_add: function(doc, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		this.frm.script_manager.copy_from_first_row("items", row, ["schedule_date"]);
	}
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

cur_frm.fields_dict['items'].grid.get_field('project_name').get_query = function(doc, cdt, cdn) {
	return {
		filters:[
			['Project', 'status', 'not in', 'Completed, Cancelled']
		]
	}
}

cur_frm.fields_dict['items'].grid.get_field('bom').get_query = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn]
	return {
		filters: [
			['BOM', 'item', '=', d.item_code],
			['BOM', 'is_active', '=', '1'],
			['BOM', 'docstatus', '=', '1']
		]
	}
}

cur_frm.cscript.get_last_purchase_rate = function(doc, cdt, cdn){
	return $c_obj(doc, 'get_last_purchase_rate', '', function(r, rt) {
		refresh_field("items");
		var doc = locals[cdt][cdn];
		cur_frm.cscript.calc_amount( doc, 2);
	});
}

cur_frm.cscript['Stop Purchase Order'] = function() {
	var doc = cur_frm.doc;
	var check = confirm(__("Do you really want to STOP ") + doc.name);

	if (check) {
		return $c('runserverobj', args={'method':'update_status', 'arg': 'Stopped', 'docs':doc}, function(r,rt) {
			cur_frm.refresh();
		});
	}
}

cur_frm.cscript['Unstop Purchase Order'] = function() {
	var doc = cur_frm.doc;
	var check = confirm(__("Do you really want to UNSTOP ") + doc.name);

	if (check) {
		return $c('runserverobj', args={'method':'update_status', 'arg': 'Submitted', 'docs':doc}, function(r,rt) {
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

	var cl = doc.items || [];

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
					out += make_row(cl[i].prevdoc_doctype, cl[i].prevdoc_docname, null,0);
				else
					out += make_row('', cl[i].prevdoc_docname,null,0);
			}
		}
	}

	out +='</table></td></tr></table></div>';

	return out;
}

cur_frm.cscript.on_submit = function(doc, cdt, cdn) {
	if(cint(frappe.boot.notification_settings.purchase_order)) {
		cur_frm.email_doc(frappe.boot.notification_settings.purchase_order_message);
	}
}



cur_frm.cscript.schedule_date = function(doc, cdt, cdn) {
	cur_frm.cscript.copy_account_in_all_row(doc, cdt, cdn, "schedule_date");
}

frappe.provide("erpnext.buying");

frappe.ui.form.on("Purchase Order", "is_subcontracted", function(frm) {
	if (frm.doc.is_subcontracted === "Yes") {
		erpnext.buying.get_default_bom(frm);
	}
});
