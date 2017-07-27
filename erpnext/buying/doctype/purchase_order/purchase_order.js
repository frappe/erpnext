// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.buying");

{% include 'erpnext/public/js/controllers/buying.js' %};

frappe.ui.form.on("Purchase Order", {
	setup: function(frm) {
		frm.custom_make_buttons = {
			'Purchase Receipt': 'Receipt',
			'Purchase Invoice': 'Invoice',
			'Stock Entry': 'Material to Supplier'
		}
	},
	onload: function(frm) {
		erpnext.queries.setup_queries(frm, "Warehouse", function() {
			return erpnext.queries.warehouse(frm.doc);
		});

		frm.set_indicator_formatter('item_code',
			function(doc) { return (doc.qty<=doc.received_qty) ? "green" : "orange" })

	}
});

erpnext.buying.PurchaseOrderController = erpnext.buying.BuyingController.extend({
	refresh: function(doc, cdt, cdn) {
		var me = this;
		this._super();
		var allow_receipt = false;
		var is_drop_ship = false;

		for (var i in cur_frm.doc.items) {
			var item = cur_frm.doc.items[i];
			if(item.delivered_by_supplier !== 1) {
				allow_receipt = true;
			} else {
				is_drop_ship = true;
			}

			if(is_drop_ship && allow_receipt) {
				break;
			}
		}

		cur_frm.set_df_property("drop_ship", "hidden", !is_drop_ship);

		if(doc.docstatus == 1 && !in_list(["Closed", "Delivered"], doc.status)) {
			if (this.frm.has_perm("submit")) {
				if(flt(doc.per_billed, 2) < 100 || doc.per_received < 100) {
					cur_frm.add_custom_button(__('Close'), this.close_purchase_order, __("Status"));
				}
			}

			if(is_drop_ship && doc.status!="Delivered"){
				cur_frm.add_custom_button(__('Delivered'),
					this.delivered_by_supplier, __("Status"));

				cur_frm.page.set_inner_btn_group_as_primary(__("Status"));
			}
		} else if(doc.docstatus===0) {
			cur_frm.cscript.add_from_mappers();
		}

		if(doc.docstatus == 1 && in_list(["Closed", "Delivered"], doc.status)) {
			if (this.frm.has_perm("submit")) {
				cur_frm.add_custom_button(__('Re-open'), this.unclose_purchase_order, __("Status"));
			}
		}

		if(doc.docstatus == 1 && doc.status != "Closed") {
			if(flt(doc.per_received, 2) < 100 && allow_receipt) {
				cur_frm.add_custom_button(__('Receipt'), this.make_purchase_receipt, __("Make"));

				if(doc.is_subcontracted==="Yes") {
					cur_frm.add_custom_button(__('Material to Supplier'),
						function() { me.make_stock_entry(); }, __("Transfer"));
				}
			}

			if(flt(doc.per_billed, 2) < 100)
				cur_frm.add_custom_button(__('Invoice'),
					this.make_purchase_invoice, __("Make"));

			if(flt(doc.per_billed)==0 && doc.status != "Delivered") {
				cur_frm.add_custom_button(__('Payment'), cur_frm.cscript.make_payment_entry, __("Make"));
			}
			cur_frm.page.set_inner_btn_group_as_primary(__("Make"));

		}
	},

	get_items_from_open_material_requests: function() {
		erpnext.utils.map_current_doc({
			method: "erpnext.stock.doctype.material_request.material_request.make_purchase_order_based_on_supplier",
			source_name: this.frm.doc.supplier,
			get_query_filters: {
				docstatus: ["!=", 2],
			}
		});
	},

	validate: function() {
		// set default schedule date as today if missing.
		(this.frm.doc.items || []).forEach(function(d) {
			if(!d.schedule_date) {
				d.schedule_date = frappe.datetime.nowdate();
			}
		})
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
		var me = this;
		this.frm.add_custom_button(__('Material Request'),
			function() {
				erpnext.utils.map_current_doc({
					method: "erpnext.stock.doctype.material_request.material_request.make_purchase_order",
					source_doctype: "Material Request",
					target: me.frm,
					setters: {
						company: me.frm.doc.company
					},
					get_query_filters: {
						material_request_type: "Purchase",
						docstatus: 1,
						status: ["!=", "Stopped"],
						per_ordered: ["<", 99.99],
					}
				})
			}, __("Add items from"));

		this.frm.add_custom_button(__('Supplier Quotation'),
			function() {
				erpnext.utils.map_current_doc({
					method: "erpnext.buying.doctype.supplier_quotation.supplier_quotation.make_purchase_order",
					source_doctype: "Supplier Quotation",
					target: me.frm,
					setters: {
						company: me.frm.doc.company
					},
					get_query_filters: {
						docstatus: 1,
						status: ["!=", "Stopped"],
					}
				})
			}, __("Add items from"));

	},

	tc_name: function() {
		this.get_terms();
	},

	items_add: function(doc, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		this.frm.script_manager.copy_from_first_row("items", row, ["schedule_date"]);
	},

	unclose_purchase_order: function(){
		cur_frm.cscript.update_status('Re-open', 'Submitted')
	},

	close_purchase_order: function(){
		cur_frm.cscript.update_status('Close', 'Closed')
	},

	delivered_by_supplier: function(){
		cur_frm.cscript.update_status('Deliver', 'Delivered')
	},

	get_last_purchase_rate: function() {
		frappe.call({
			"method": "get_last_purchase_rate",
			"doc": cur_frm.doc,
			callback: function(r, rt) {
				cur_frm.dirty();
				cur_frm.cscript.calculate_taxes_and_totals();
			}
		})
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

cur_frm.fields_dict['items'].grid.get_field('project').get_query = function(doc, cdt, cdn) {
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
