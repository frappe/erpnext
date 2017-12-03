// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Production Plan', {
	setup: function(frm) {
		['warehouse'].forEach((fieldname) => {
			frm.fields_dict['po_items'].grid.get_field(fieldname).get_query = function(doc) {
				return {
					filters: {
						company: doc.company
					}
				}
			}
		});

		frm.fields_dict['po_items'].grid.get_field('bom_no').get_query = function(doc, cdt, cdn) {
			var d = locals[cdt][cdn];
			if (d.item_code) {
				return {
					query: "erpnext.controllers.queries.bom",
					filters:{'item': cstr(d.item_code)}
				}
			} else frappe.msgprint(__("Please enter Item first"));
		}
	},

	refresh: function(frm) {
		if (frm.doc.docstatus === 1) {
			frm.trigger("show_progress");
		}

		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Production Order"), ()=> {
				frm.trigger("make_production_order");
			}, __("Make"));
		}
		
		if (frm.doc.docstatus === 1 && frm.doc.status != 'Material Requested') {
			frm.add_custom_button(__("Material Request"), ()=> {
				frm.trigger("make_material_request");
			}, __("Make"));
		}

		frm.trigger("material_requirement");
		frm.page.set_inner_btn_group_as_primary(__("Make"));
	},

	make_production_order: function(frm) {
		frappe.call({
			method: "make_production_order",
			freeze: true,
			doc: frm.doc,
			callback: function(r) {
				frm.reload_doc();
			}
		});
	},

	make_material_request: function(frm) {
		frappe.call({
			method: "make_material_request",
			freeze: true,
			doc: frm.doc,
			callback: function(r) {
				frm.reload_doc();
			}
		});
	},

	get_sales_orders: function(frm) {
		frappe.call({
			method: "get_open_sales_orders",
			doc: frm.doc,
			callback: function(r) {
				refresh_field("sales_orders");
			}
		});
	},

	get_material_request: function(frm) {
		frappe.call({
			method: "get_pending_material_requests",
			doc: frm.doc,
			callback: function() {
				refresh_field('material_requests')
			}
		})
	},

	get_items: function(frm) {
		frappe.call({
			method: "get_items",
			freeze: true,
			doc: frm.doc,
			callback: function() {
				refresh_field('po_items')
			}
		})
	},
	
	get_items_for_mr: function(frm) {
		frappe.call({
			method: "get_items_for_material_requests",
			freeze: true,
			doc: frm.doc,
			callback: function() {
				refresh_field('mr_items')
			}
		})
	},

	show_progress: function(frm) {
		var bars = [];
		var message = '';
		var added_min = false;
		var title = '';

		// produced qty
		item_wise_qty = {};
		frm.doc.items.forEach((data) => {
			if(!item_wise_qty[data.item_code]) {
				item_wise_qty[data.item_code] = data.produced_qty;
			} else {
				item_wise_qty[data.item_code] += data.produced_qty;
			}
		})

		if (item_wise_qty) {
			for (var key in item_wise_qty) {
				title += __('Item {0}: {1} qty produced, ', [key, item_wise_qty[key]]);
			}
		}

		bars.push({
			'title': title,
			'width': (frm.doc.total_produced_qty / frm.doc.total_planned_qty * 100) + '%',
			'progress_class': 'progress-bar-success'
		});
		if (bars[0].width == '0%') {
			bars[0].width = '0.5%';
			added_min = 0.5;
		}
		message = title;
		frm.dashboard.add_progress(__('Status'), bars, message);
	},
});
