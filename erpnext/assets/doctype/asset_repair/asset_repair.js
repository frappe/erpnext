// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Asset Repair", {
	setup: function (frm) {
		frm.ignore_doctypes_on_cancel_all = ["Serial and Batch Bundle"];

		frm.fields_dict.cost_center.get_query = function (doc) {
			return {
				filters: {
					is_group: 0,
					company: doc.company,
				},
			};
		};

		frm.fields_dict.project.get_query = function (doc) {
			return {
				filters: {
					company: doc.company,
				},
			};
		};

		frm.set_query("asset", function () {
			return {
				filters: {
					company: frm.doc.company,
					docstatus: 1,
				},
			};
		});

		frm.set_query("purchase_invoice", "invoices", function () {
			return {
				query: "erpnext.assets.doctype.asset_repair.asset_repair.get_purchase_invoice",
				filters: {
					company: frm.doc.company,
				},
			};
		});

		frm.set_query("expense_account", "invoices", function (doc, cdt, cdn) {
			let row = locals[cdt][cdn];
			return {
				query: "erpnext.assets.doctype.asset_repair.asset_repair.get_expense_accounts",
				filters: {
					purchase_invoice: row.purchase_invoice,
				},
			};
		});

		frm.set_query("warehouse", "stock_items", function () {
			return {
				filters: {
					is_group: 0,
					company: frm.doc.company,
				},
			};
		});

		frm.set_query("serial_and_batch_bundle", "stock_items", (doc, cdt, cdn) => {
			let row = locals[cdt][cdn];
			return {
				filters: {
					item_code: row.item_code,
					voucher_type: doc.doctype,
					voucher_no: ["in", [doc.name, ""]],
					is_cancelled: 0,
				},
			};
		});
	},

	refresh: function (frm) {
		frm.events.show_general_ledger(frm);

		let sbb_field = frm.get_docfield("stock_items", "serial_and_batch_bundle");
		if (sbb_field) {
			sbb_field.get_route_options_for_new_doc = (row) => {
				return {
					item_code: row.doc.item_code,
					voucher_type: frm.doc.doctype,
				};
			};
		}
	},

	repair_status: (frm) => {
		if (frm.doc.completion_date && frm.doc.repair_status == "Completed") {
			frappe.call({
				method: "erpnext.assets.doctype.asset_repair.asset_repair.get_downtime",
				args: {
					failure_date: frm.doc.failure_date,
					completion_date: frm.doc.completion_date,
				},
				callback: function (r) {
					if (r.message) {
						frm.set_value("downtime", r.message + " Hrs");
					}
				},
			});
		}

		if (frm.doc.repair_status == "Completed" && !frm.doc.completion_date) {
			frm.set_value("completion_date", frappe.datetime.now_datetime());
		}
	},

	stock_items_on_form_rendered() {
		erpnext.setup_serial_or_batch_no();
	},

	stock_consumption: function (frm) {
		if (!frm.doc.stock_consumption) {
			frm.clear_table("stock_items");
			frm.refresh_field("stock_items");
		}
	},

	purchase_invoice: function (frm) {
		if (frm.doc.purchase_invoice) {
			frappe.call({
				method: "frappe.client.get_value",
				args: {
					doctype: "Purchase Invoice",
					fieldname: "base_net_total",
					filters: { name: frm.doc.purchase_invoice },
				},
				callback: function (r) {
					if (r.message) {
						frm.set_value("repair_cost", r.message.base_net_total);
					}
				},
			});
		} else {
			frm.set_value("repair_cost", 0);
		}
	},

	show_general_ledger: (frm) => {
		if (frm.doc.docstatus > 0) {
			frm.add_custom_button(
				__("Accounting Ledger"),
				function () {
					frappe.route_options = {
						voucher_no: frm.doc.name,
						from_date: frm.doc.posting_date,
						to_date: moment(frm.doc.modified).format("YYYY-MM-DD"),
						company: frm.doc.company,
						categorize_by: "",
						show_cancelled_entries: frm.doc.docstatus === 2,
					};
					frappe.set_route("query-report", "General Ledger");
				},
				__("View")
			);
		}
	},
});

frappe.ui.form.on("Asset Repair Consumed Item", {
	warehouse: function (frm, cdt, cdn) {
		var item = locals[cdt][cdn];

		if (!item.item_code) {
			frappe.msgprint(__("Please select an item code before setting the warehouse."));
			frappe.model.set_value(cdt, cdn, "warehouse", "");
			return;
		}

		let item_args = {
			item_code: item.item_code,
			warehouse: item.warehouse,
			qty: item.consumed_quantity,
			serial_no: item.serial_no,
			company: frm.doc.company,
		};

		frappe.call({
			method: "erpnext.stock.utils.get_incoming_rate",
			args: {
				args: item_args,
			},
			callback: function (r) {
				frappe.model.set_value(cdt, cdn, "valuation_rate", r.message);
			},
		});
	},

	consumed_quantity: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "total_value", row.consumed_quantity * row.valuation_rate);
	},

	pick_serial_and_batch(frm, cdt, cdn) {
		let item = locals[cdt][cdn];
		let doc = frm.doc;

		frappe.db.get_value("Item", item.item_code, ["has_batch_no", "has_serial_no"]).then((r) => {
			if (r.message && (r.message.has_batch_no || r.message.has_serial_no)) {
				item.has_serial_no = r.message.has_serial_no;
				item.has_batch_no = r.message.has_batch_no;
				item.qty = item.consumed_quantity;
				item.type_of_transaction = item.consumed_quantity > 0 ? "Outward" : "Inward";

				item.title = item.has_serial_no ? __("Select Serial No") : __("Select Batch No");

				if (item.has_serial_no && item.has_batch_no) {
					item.title = __("Select Serial and Batch");
				}
				frm.doc.posting_date = frappe.datetime.get_today();
				frm.doc.posting_time = frappe.datetime.now_time();

				new erpnext.SerialBatchPackageSelector(frm, item, (r) => {
					if (r) {
						frappe.model.set_value(item.doctype, item.name, {
							serial_and_batch_bundle: r.name,
							use_serial_batch_fields: 0,
							valuation_rate: r.avg_rate,
							consumed_quantity: Math.abs(r.total_qty),
						});
					}
				});
			}
		});
	},
});
