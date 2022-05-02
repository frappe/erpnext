// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Asset Repair', {
	setup: function(frm) {
		frm.fields_dict.cost_center.get_query = function(doc) {
			return {
				filters: {
					'is_group': 0,
					'company': doc.company
				}
			};
		};

		frm.fields_dict.project.get_query = function(doc) {
			return {
				filters: {
					'company': doc.company
				}
			};
		};

		frm.fields_dict.warehouse.get_query = function(doc) {
			return {
				filters: {
					'is_group': 0,
					'company': doc.company
				}
			};
		};
	},

	refresh: function(frm) {
		if (frm.doc.docstatus) {
			frm.add_custom_button(__("View General Ledger"), function() {
				frappe.route_options = {
					"voucher_no": frm.doc.name
				};
				frappe.set_route("query-report", "General Ledger");
			});
		}
	},

	repair_status: (frm) => {
		if (frm.doc.completion_date && frm.doc.repair_status == "Completed") {
			frappe.call ({
				method: "erpnext.assets.doctype.asset_repair.asset_repair.get_downtime",
				args: {
					"failure_date":frm.doc.failure_date,
					"completion_date":frm.doc.completion_date
				},
				callback: function(r) {
					if(r.message) {
						frm.set_value("downtime", r.message + " Hrs");
					}
				}
			});
		}

		if (frm.doc.repair_status == "Completed") {
			frm.set_value('completion_date', frappe.datetime.now_datetime());
		}
	},

	stock_items_on_form_rendered() {
		erpnext.setup_serial_or_batch_no();
	}
});

frappe.ui.form.on('Asset Repair Consumed Item', {
	item_code: function(frm, cdt, cdn) {
		var item = locals[cdt][cdn];

		let item_args = {
			'item_code': item.item_code,
			'warehouse': frm.doc.warehouse,
			'qty': item.consumed_quantity,
			'serial_no': item.serial_no,
			'company': frm.doc.company
		};

		frappe.call({
			method: 'erpnext.stock.utils.get_incoming_rate',
			args: {
				args: item_args
			},
			callback: function(r) {
				frappe.model.set_value(cdt, cdn, 'valuation_rate', r.message);
			}
		});
	},

	consumed_quantity: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, 'total_value', row.consumed_quantity * row.valuation_rate);
	},
});
