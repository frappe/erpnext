// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.buying");

{% include 'buying/doctype/purchase_common/purchase_common.js' %};

frappe.ui.form.on("Purchase Order", {
	onload: function(frm) {
		erpnext.queries.setup_queries(frm, "Warehouse", function() {
			return erpnext.queries.warehouse(frm.doc);
		});
	}
});

erpnext.buying.PurchaseOrderController = erpnext.buying.BuyingController.extend({
	refresh: function(doc, cdt, cdn) {
		var me = this;
		this._super();
		// this.frm.dashboard.reset();
		var allow_receipt = false;
		var is_drop_ship = false;

		for (var i in cur_frm.doc.items) {
			var item = cur_frm.doc.items[i];
			if(item.delivered_by_supplier !== 1) {
				allow_receipt = true;
			}

			else {
				is_drop_ship = true
			}

			if(is_drop_ship && allow_receipt) {
				break;
			}
		}

		cur_frm.set_df_property("drop_ship", "hidden", !is_drop_ship);

		if(doc.docstatus == 1 && !in_list(["Stopped", "Closed", "Delivered"], doc.status)) {
			if (this.frm.has_perm("submit")) {
				if(flt(doc.per_billed, 2) < 100 || doc.per_received < 100) {
					cur_frm.add_custom_button(__('Stop'), this.stop_purchase_order);
				}

				cur_frm.add_custom_button(__('Close'), this.close_purchase_order);
			}

			if(flt(doc.per_billed)==0) {
				cur_frm.add_custom_button(__('Payment'), cur_frm.cscript.make_bank_entry);
			}

			if(is_drop_ship && doc.status!="Delivered"){
				cur_frm.add_custom_button(__('Mark as Delivered'),
					 this.delivered_by_supplier).addClass("btn-primary");
			}
		} else if(doc.docstatus===0) {
			cur_frm.cscript.add_from_mappers();
		}

		if(doc.docstatus == 1 && !in_list(["Stopped", "Closed"], doc.status)) {
			if(flt(doc.per_received, 2) < 100 && allow_receipt) {
				cur_frm.add_custom_button(__('Receive'), this.make_purchase_receipt).addClass("btn-primary");

				if(doc.is_subcontracted==="Yes") {
					cur_frm.add_custom_button(__('Transfer Material to Supplier'),
						function() { me.make_stock_entry(); });
				}
			}

			if(flt(doc.per_billed, 2) < 100)
				cur_frm.add_custom_button(__('Invoice'),
					this.make_purchase_invoice).addClass("btn-primary");
		}

		if(doc.docstatus == 1 && in_list(["Stopped", "Closed", "Delivered"], doc.status)) {
			if (this.frm.has_perm("submit")) {
				cur_frm.add_custom_button(__('Re-open'), this.unstop_purchase_order).addClass("btn-primary");
			}
		}
	},

	make_stock_entry: function() {
		var items = $.map(cur_frm.doc.items, function(d) { return d.bom ? d.item_code : false; });
		var me = this;

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
			}
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
			}
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
			}
		);
	},

	tc_name: function() {
		this.get_terms();
	},

	items_add: function(doc, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		this.frm.script_manager.copy_from_first_row("items", row, ["schedule_date"]);
	},

	make_bank_entry: function() {
		return frappe.call({
			method: "erpnext.accounts.doctype.journal_entry.journal_entry.get_payment_entry_against_order",
			args: {
				"dt": "Purchase Order",
				"dn": cur_frm.doc.name
			},
			callback: function(r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	},

	stop_purchase_order: function(){
		cur_frm.cscript.update_status('Stop', 'Stopped')
	},

	unstop_purchase_order: function(){
		cur_frm.cscript.update_status('Re-open', 'Submitted')
	},

	close_purchase_order: function(){
		cur_frm.cscript.update_status('Close', 'Closed')
	},

	delivered_by_supplier: function(){
		cur_frm.cscript.update_status('Deliver', 'Delivered')
	}

});

// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, new erpnext.buying.PurchaseOrderController({frm: cur_frm}));

cur_frm.cscript.update_status= function(label, status){
	frappe.call({
		method: "erpnext.buying.doctype.purchase_order.purchase_order.update_status",
		args: {status: status, name: cur_frm.doc.name},
		callback: function(r) {
			cur_frm.set_value("status", status);
			cur_frm.reload_doc();
		}
	})
}

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
	erpnext.utils.copy_value_in_all_row(doc, cdt, cdn, "items", "schedule_date");
}

frappe.provide("erpnext.buying");

frappe.ui.form.on("Purchase Order", "is_subcontracted", function(frm) {
	if (frm.doc.is_subcontracted === "Yes") {
		erpnext.buying.get_default_bom(frm);
	}
});
