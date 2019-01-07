// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// eslint-disable-next-line
{% include 'erpnext/public/js/controllers/buying.js' %};

frappe.ui.form.on('Material Request', {
	setup: function(frm) {
		frm.custom_make_buttons = {
			'Stock Entry': 'Issue Material',
			'Purchase Order': 'Purchase Order',
			'Request for Quotation': 'Request for Quotation',
			'Supplier Quotation': 'Supplier Quotation',
			'Work Order': 'Work Order'
		};

		// formatter for material request item
		frm.set_indicator_formatter('item_code',
			function(doc) { return (doc.qty<=doc.ordered_qty) ? "green" : "orange"; });

		frm.set_query("item_code", "items", function() {
			return {
				query: "erpnext.controllers.queries.item_query"
			};
		});
	},

	onload: function(frm) {
		// add item, if previous view was item
		erpnext.utils.add_item(frm);

		// set schedule_date
		set_schedule_date(frm);
		frm.fields_dict["items"].grid.get_field("warehouse").get_query = function(doc) {
			return {
				filters: {'company': doc.company}
			};
		};
	},

	refresh: function(frm) {
		frm.events.make_custom_buttons(frm);
		frm.toggle_reqd('customer', frm.doc.material_request_type=="Customer Provided");
	},

	make_custom_buttons: function(frm) {
		if (frm.doc.docstatus==0) {
			frm.add_custom_button(__("Bill of Materials"),
				() => frm.events.get_items_from_bom(frm), __("Get items from"));
		}

		if (frm.doc.docstatus == 1 && frm.doc.status != 'Stopped') {
			if (flt(frm.doc.per_ordered, 2) < 100) {
				// make
				if (frm.doc.material_request_type === "Material Transfer") {
					frm.add_custom_button(__("Transfer Material"),
						() => frm.events.make_stock_entry(frm), __('Create'));
				}

				if (frm.doc.material_request_type === "Material Issue") {
					frm.add_custom_button(__("Issue Material"),
						() => frm.events.make_stock_entry(frm), __('Create'));
				}

				if (frm.doc.material_request_type === "Customer Provided") {
					frm.add_custom_button(__("Material Receipt"),
						() => frm.events.make_stock_entry(frm), __('Create'));
				}

				if (frm.doc.material_request_type === "Purchase") {
					frm.add_custom_button(__('Purchase Order'),
						() => frm.events.make_purchase_order(frm), __('Create'));
				}

				if (frm.doc.material_request_type === "Purchase") {
					frm.add_custom_button(__("Request for Quotation"),
						() => frm.events.make_request_for_quotation(frm), __('Create'));
				}

				if (frm.doc.material_request_type === "Purchase") {
					frm.add_custom_button(__("Supplier Quotation"),
						() => frm.events.make_supplier_quotation(frm), __('Create'));
				}

				if (frm.doc.material_request_type === "Manufacture") {
					frm.add_custom_button(__("Work Order"),
						() => frm.events.raise_work_orders(frm), __('Create'));
				}

				frm.page.set_inner_btn_group_as_primary(__('Create'));

				// stop
				frm.add_custom_button(__('Stop'),
					() => frm.events.update_status(frm, 'Stop'));

			}
		}

		if (frm.doc.docstatus===0) {
			frm.add_custom_button(__('Sales Order'), () => frm.events.get_items_from_sales_order(frm),
				__("Get items from"));
		}

		if (frm.doc.docstatus == 1 && frm.doc.status == 'Stopped') {
			frm.add_custom_button(__('Re-open'), () => frm.events.update_status(frm, 'Submitted'));
		}
	},

	update_status: function(frm, stop_status) {
		frappe.call({
			method: 'erpnext.stock.doctype.material_request.material_request.update_status',
			args: { name: frm.doc.name, status: stop_status },
			callback(r) {
				if (!r.exc) {
					frm.reload_doc();
				}
			}
		});
	},

	get_items_from_sales_order: function(frm) {
		erpnext.utils.map_current_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_material_request",
			source_doctype: "Sales Order",
			target: frm,
			setters: {
				company: frm.doc.company
			},
			get_query_filters: {
				docstatus: 1,
				status: ["!=", "Closed"],
				per_delivered: ["<", 99.99],
			}
		});
	},

	get_item_data: function(frm, item) {
		frm.call({
			method: "erpnext.stock.get_item_details.get_item_details",
			child: item,
			args: {
				args: {
					item_code: item.item_code,
					warehouse: item.warehouse,
					doctype: frm.doc.doctype,
					buying_price_list: frappe.defaults.get_default('buying_price_list'),
					currency: frappe.defaults.get_default('Currency'),
					name: frm.doc.name,
					qty: item.qty || 1,
					stock_qty: item.stock_qty,
					company: frm.doc.company,
					conversion_rate: 1,
					material_request_type: frm.doc.material_request_type,
					plc_conversion_rate: 1,
					rate: item.rate,
					conversion_factor: item.conversion_factor
				}
			},
			callback: function(r) {
				const d = item;
				if(!r.exc) {
					$.each(r.message, function(k, v) {
						if(!d[k]) d[k] = v;
					});
				}
			}
		});
	},

	get_items_from_bom: function(frm) {
		var d = new frappe.ui.Dialog({
			title: __("Get Items from BOM"),
			fields: [
				{"fieldname":"bom", "fieldtype":"Link", "label":__("BOM"),
					options:"BOM", reqd: 1, get_query: function() {
						return {filters: { docstatus:1 }};
					}},
				{"fieldname":"warehouse", "fieldtype":"Link", "label":__("Warehouse"),
					options:"Warehouse", reqd: 1},
				{"fieldname":"qty", "fieldtype":"Float", "label":__("Quantity"),
					reqd: 1, "default": 1},
				{"fieldname":"fetch_exploded", "fieldtype":"Check",
					"label":__("Fetch exploded BOM (including sub-assemblies)"), "default":1},
				{fieldname:"fetch", "label":__("Get Items from BOM"), "fieldtype":"Button"}
			]
		});
		d.get_input("fetch").on("click", function() {
			var values = d.get_values();
			if(!values) return;
			values["company"] = frm.doc.company;
			frappe.call({
				method: "erpnext.manufacturing.doctype.bom.bom.get_bom_items",
				args: values,
				callback: function(r) {
					if (!r.message) {
						frappe.throw(__("BOM does not contain any stock item"));
					} else {
						erpnext.utils.remove_empty_first_row(frm, "items");
						$.each(r.message, function(i, item) {
							var d = frappe.model.add_child(cur_frm.doc, "Material Request Item", "items");
							d.item_code = item.item_code;
							d.item_name = item.item_name;
							d.description = item.description;
							d.warehouse = values.warehouse;
							d.uom = item.stock_uom;
							d.stock_uom = item.stock_uom;
							d.conversion_factor = 1;
							d.qty = item.qty;
						});
					}
					d.hide();
					refresh_field("items");
				}
			});
		});
		d.show();
	},

	make_purchase_order: function(frm) {
		frappe.prompt(
			{fieldname:'default_supplier', label: __('For Default Supplier (optional)'), fieldtype: 'Link', options: 'Supplier'},
			(values) => {
				frappe.model.open_mapped_doc({
					method: "erpnext.stock.doctype.material_request.material_request.make_purchase_order",
					frm: frm,
					args: { default_supplier: values.default_supplier },
					run_link_triggers: true
				});
			}
		)
	},

	make_request_for_quotation: function(frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.stock.doctype.material_request.material_request.make_request_for_quotation",
			frm: frm,
			run_link_triggers: true
		});
	},

	make_supplier_quotation: function(frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.stock.doctype.material_request.material_request.make_supplier_quotation",
			frm: frm
		});
	},

	make_stock_entry: function(frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.stock.doctype.material_request.material_request.make_stock_entry",
			frm: frm
		});
	},

	raise_work_orders: function(frm) {
		frappe.call({
			method:"erpnext.stock.doctype.material_request.material_request.raise_work_orders",
			args: {
				"material_request": frm.doc.name
			},
			callback: function(r) {
				if(r.message.length) {
					frm.reload_doc();
				}
			}
		});
	},
	material_request_type: function(frm) {
		frm.toggle_reqd('customer', frm.doc.material_request_type=="Customer Provided");
	},

});

frappe.ui.form.on("Material Request Item", {
	qty: function (frm, doctype, name) {
		var d = locals[doctype][name];
		if (flt(d.qty) < flt(d.min_order_qty)) {
			frappe.msgprint(__("Warning: Material Requested Qty is less than Minimum Order Qty"));
		}

		const item = locals[doctype][name];
		frm.events.get_item_data(frm, item);
	},

	rate: function(frm, doctype, name) {
		const item = locals[doctype][name];
		frm.events.get_item_data(frm, item);
	},

	item_code: function(frm, doctype, name) {
		const item = locals[doctype][name];
		item.rate = 0;
		set_schedule_date(frm);
		frm.events.get_item_data(frm, item);
	},

	schedule_date: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.schedule_date) {
			if(!frm.doc.schedule_date) {
				erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, "items", "schedule_date");
			} else {
				set_schedule_date(frm);
			}
		}
	}
});

erpnext.buying.MaterialRequestController = erpnext.buying.BuyingController.extend({
	tc_name: function() {
		this.get_terms();
	},

	item_code: function() {
		// to override item code trigger from transaction.js
	},

	validate_company_and_party: function() {
		return true;
	},

	calculate_taxes_and_totals: function() {
		return;
	},

	validate: function() {
		set_schedule_date(this.frm);
	},

	items_add: function(doc, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		if(doc.schedule_date) {
			row.schedule_date = doc.schedule_date;
			refresh_field("schedule_date", cdn, "items");
		} else {
			this.frm.script_manager.copy_from_first_row("items", row, ["schedule_date"]);
		}
	},

	items_on_form_rendered: function() {
		set_schedule_date(this.frm);
	},

	schedule_date: function() {
		set_schedule_date(this.frm);
	}
});

// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, new erpnext.buying.MaterialRequestController({frm: cur_frm}));

function set_schedule_date(frm) {
	if(frm.doc.schedule_date){
		erpnext.utils.copy_value_in_all_rows(frm.doc, frm.doc.doctype, frm.doc.name, "items", "schedule_date");
	}
}
