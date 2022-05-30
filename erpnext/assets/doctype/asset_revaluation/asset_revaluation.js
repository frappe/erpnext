// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.accounts.dimensions");

frappe.ui.form.on("Asset Revaluation", {
	setup: function (frm) {
		frm.add_fetch("company", "cost_center", "cost_center");

		frm.set_query("cost_center", function () {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0
				}
			};
		});

		frm.set_query("asset", function () {
			return {
				filters: {
					calculate_depreciation: 1,
					docstatus: 1
				}
			};
		});

		frm.set_query("serial_no", function () {
			return {
				filters: {
					asset: frm.doc.asset,
				}
			};
		});
	},

	onload: function (frm) {
		if (frm.is_new() && frm.doc.asset) {
			frm.trigger("set_current_asset_value");
		}

		erpnext.accounts.dimensions.setup_dimension_filters(frm, frm.doctype);
	},

	refresh: function (frm) {
		frm.trigger("toggle_serial_no_and_num_of_assets");
		frm.trigger("toggle_finance_books");
	},

	company: function (frm) {
		erpnext.accounts.dimensions.update_dimension(frm, frm.doctype);
	},

	asset: function (frm) {
		frm.trigger("set_current_asset_value");
		frm.trigger("toggle_serial_no_and_num_of_assets");
		frm.trigger("toggle_finance_books");
	},

	finance_book: function (frm) {
		frm.trigger("set_current_asset_value");
	},

	serial_no: function (frm) {
		frm.trigger("set_current_asset_value");
	},

	set_current_asset_value: function (frm) {
		if (frm.doc.asset) {
			frm.call({
				method: "erpnext.assets.doctype.asset_revaluation.asset_revaluation.get_current_asset_value",
				args: {
					asset: frm.doc.asset,
					serial_no: frm.doc.serial_no,
					finance_book: frm.doc.finance_book
				},
				callback: function (r) {
					if (r.message) {
						frm.set_value("current_asset_value", r.message);
					}
				}
			});
		}
	},

	toggle_serial_no_and_num_of_assets: (frm) => {
		if (frm.doc.asset) {
			frappe.db.get_value("Asset", frm.doc.asset, ["is_serialized_asset", "num_of_assets"], (r) => {
				if (r && r.is_serialized_asset) {
					frm.set_df_property("serial_no", "hidden", 0);
					frm.set_df_property("serial_no", "reqd", 1);

					frm.set_value("num_of_assets", 0);
					frm.set_df_property("num_of_assets", "hidden", 1);
					frm.set_df_property("num_of_assets", "reqd", 0);
				} else {
					frm.set_df_property("serial_no", "hidden", 1);
					frm.set_df_property("serial_no", "reqd", 0);
					frm.set_value("serial_no", "");

					if (r.num_of_assets > 1) {
						if (!frm.doc.num_of_assets) {
							frm.set_value("num_of_assets", r.num_of_assets);
						}

						frm.set_df_property("num_of_assets", "hidden", 0);
						frm.set_df_property("num_of_assets", "reqd", 1);
					} else {
						frm.set_df_property("num_of_assets", "reqd", 0);
					}
				}
			});
		} else {
			frm.set_df_property("serial_no", "hidden", 1);
			frm.set_df_property("num_of_assets", "hidden", 1);
		}
	},

	toggle_finance_books: (frm) => {
		if (frm.doc.asset) {
			frappe.db.get_single_value("Accounts Settings", "enable_finance_books")
				.then((value) => {
					frm.toggle_display("finance_book", value);
				});
		} else {
			frm.set_df_property("finance_book", "hidden", 1);
		}
	}
});
