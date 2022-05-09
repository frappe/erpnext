// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.asset");
frappe.provide("erpnext.accounts.dimensions");

frappe.ui.form.on("Asset", {
	onload: function (frm) {
		frm.set_query("item_code", function () {
			return {
				"filters": {
					"disabled": 0,
					"is_fixed_asset": 1,
					"is_stock_item": 0
				}
			};
		});

		frm.set_query("department", function () {
			return {
				"filters": {
					"company": frm.doc.company,
				}
			};
		});

		erpnext.accounts.dimensions.setup_dimension_filters(frm, frm.doctype);
	},

	company: function (frm) {
		erpnext.accounts.dimensions.update_dimension(frm, frm.doctype);
	},

	setup: function (frm) {
		frm.set_query("purchase_receipt", (doc) => {
			return {
				query: "erpnext.controllers.queries.get_purchase_receipts",
				filters: { item_code: doc.item_code }
			}
		});

		frm.set_query("purchase_invoice", (doc) => {
			return {
				query: "erpnext.controllers.queries.get_purchase_invoices",
				filters: { item_code: doc.item_code }
			}
		});
	},

	refresh: function (frm) {
		frm.trigger("toggle_reference_doc");
		frm.trigger("toggle_depreciation_details");
		frm.trigger("toggle_asset_value");

		if (frm.doc.docstatus == 1) {
			if (frm.doc.is_serialized_asset) {
				frm.trigger("toggle_display_create_serial_nos_button");
			} else {
				if (frm.doc.num_of_assets > 1) {
					frm.add_custom_button(__("Split Asset"), function () {
						frm.trigger("split_asset");
					}, __("Manage"));
				}

				if (in_list(["Submitted", "Partially Depreciated", "Fully Depreciated"], frm.doc.status)) {
					frm.add_custom_button(__("Transfer Asset"), function () {
						frm.trigger("transfer_asset");
					}, __("Manage"));

					frm.add_custom_button(__("Scrap Asset"), function () {
						frm.trigger("scrap_asset");
					}, __("Manage"));

					frm.add_custom_button(__("Sell Asset"), function () {
						frm.trigger("make_sales_invoice");
					}, __("Manage"));
				} else if (frm.doc.status == "Scrapped") {
					frm.add_custom_button(__("Restore Asset"), function () {
						frm.trigger("restore_asset");
					}, __("Manage"));
				}

				if (frm.doc.maintenance_required && !frm.doc.maintenance_schedule) {
					frm.add_custom_button(__("Maintain Asset"), function () {
						frm.trigger("create_asset_maintenance");
					}, __("Manage"));
				}

				frm.add_custom_button(__("Repair Asset"), function () {
					frm.trigger("create_asset_repair");
				}, __("Manage"));

				if (frm.doc.status != "Fully Depreciated") {
					frm.add_custom_button(__("Revalue Asset"), function () {
						frm.trigger("create_asset_revaluation");
					}, __("Manage"));
				}

				if (frm.doc.calculate_depreciation) {
					frm.trigger("setup_chart");
				} else {
					frm.add_custom_button(__("Create Depreciation Entry"), function () {
						frm.trigger("create_depreciation_entry");
					}, __("Manage"));
				}

				if (frm.doc.purchase_receipt || !frm.doc.is_existing_asset) {
					frm.add_custom_button(__("View General Ledger"), function () {
						frappe.route_options = {
							"voucher_no": frm.doc.name,
							"from_date": frm.doc.available_for_use_date,
							"to_date": frm.doc.available_for_use_date,
							"company": frm.doc.company
						};
						frappe.set_route("query-report", "General Ledger");
					}, __("Manage"));
				}
			}
		}
	},

	is_existing_asset: function (frm) {
		frm.trigger("toggle_reference_doc");
	},

	toggle_reference_doc: function (frm) {
		if (frm.doc.purchase_receipt && frm.doc.purchase_invoice && frm.doc.docstatus === 1) {
			frm.set_df_property("purchase_invoice", "read_only", 1);
			frm.set_df_property("purchase_receipt", "read_only", 1);
		}
		else if (frm.doc.is_existing_asset) {
			frm.toggle_reqd("purchase_receipt", 0);
			frm.toggle_reqd("purchase_invoice", 0);
			frm.toggle_display("purchase_receipt", 0);
			frm.toggle_display("purchase_invoice", 0);
		}
		else if (frm.doc.purchase_receipt) {
			// if PR is entered, PI is hidden and no longer mandatory
			frm.toggle_reqd("purchase_invoice", 0);
			frm.set_df_property("purchase_invoice", "read_only", 1);
		}
		else if (frm.doc.purchase_invoice) {
			// if PI is entered, PR  is hidden and no longer mandatory
			frm.toggle_reqd("purchase_receipt", 0);
			frm.set_df_property("purchase_receipt", "read_only", 1);
		}
		else {
			frm.toggle_reqd("purchase_receipt", 1);
			frm.toggle_reqd("purchase_invoice", 1);
			frm.set_df_property("purchase_receipt", "read_only", 0);
			frm.set_df_property("purchase_invoice", "read_only", 0);
			frm.toggle_display("purchase_receipt", 1);
			frm.toggle_display("purchase_invoice", 1);
		}
	},

	toggle_display_create_serial_nos_button: function (frm) {
		if (frm.doc.is_serialized_asset) {
			if (!frm.doc.is_existing_asset) {
				frappe.call({
					method: "erpnext.controllers.base_asset.get_purchase_details",
					args: {
						asset: frm.doc
					},
					callback: function (r) {
						if (r.message) {
							frappe.call({
								method: "erpnext.controllers.base_asset.get_num_of_items_in_purchase_doc",
								args: {
									asset: frm.doc,
									purchase_doctype: r.message[0],
									purchase_docname: r.message[1]
								},
								callback: function (r) {
									if (r.message) {
										if (r.message > frm.doc.num_of_assets) {
											frm.add_custom_button(__("Create Serial Numbers"), function () {
												frm.trigger("create_asset_serial_nos");
											});
										}
									}
								}
							});
						}
					}
				});
			} else {
				frm.add_custom_button(__("Create Serial Numbers"), function () {
					frm.trigger("create_asset_serial_nos");
				});
			}
		}
	},

	create_asset_serial_nos: function (frm) {
		var dialog = new frappe.ui.Dialog({
			title: __("Create Additional Serial Nos"),
			fields: [
				{
					"label": "Number of Serial Nos to be Created",
					"fieldname": "additional_num_of_assets",
					"fieldtype": "Int",
					"reqd": 1,
					"default": 1
				},
			],
			primary_action_label: __("Create"),
			primary_action: function () {
				var data = dialog.get_values();
				frappe.call({
					method: "erpnext.assets.doctype.asset_serial_no.asset_serial_no.create_asset_serial_no_docs",
					args: {
						asset: frm.doc.name,
						num_of_assets: data.additional_num_of_assets
					},
					callback: function () {
						dialog.hide();
						frm.refresh();
						frm.refresh_field("num_of_assets");
					}
				});
			},
		});
		dialog.show();
	},

	split_asset: function (frm) {
		var dialog = new frappe.ui.Dialog({
			title: __("Split Asset"),
			fields: [
				{
					"label": "Current Number of Assets",
					"fieldname": "current_num_of_assets",
					"fieldtype": "Int",
					"read_only": 1,
					"default": frm.doc.num_of_assets
				},
				{
					"label": "Number of Assets to be Separated",
					"fieldname": "num_of_assets_to_be_separated",
					"fieldtype": "Int",
					"reqd": 1,
					"default": 1
				},
			],
			primary_action_label: __("Split"),
			primary_action: function () {
				var data = dialog.get_values();
				frappe.call({
					method: "erpnext.assets.doctype.asset.asset.split_asset",
					args: {
						asset: frm.doc.name,
						num_of_assets_to_be_separated: data.num_of_assets_to_be_separated
					},
					callback: function () {
						dialog.hide();
						frm.refresh();
						frm.refresh_field("num_of_assets");
					}
				});
			},
		});
		dialog.show();
	},

	transfer_asset: function (frm) {
		frappe.call({
			method: "erpnext.controllers.base_asset.transfer_asset",
			freeze: true,
			args: {
				"asset": frm.doc.name,
				"num_of_assets": frm.doc.num_of_assets,
				"purpose": "Transfer",
				"source_location": frm.doc.location,
				"company": frm.doc.company
			},
			callback: function (r) {
				if (r.message) {
					var doc = frappe.model.sync(r.message)[0];
					frappe.set_route("Form", doc.doctype, doc.name);
				}
			}
		});
	},

	make_sales_invoice: function (frm) {
		frappe.call({
			args: {
				"asset": frm.doc.name,
				"item_code": frm.doc.item_code,
				"company": frm.doc.company
			},
			method: "erpnext.controllers.base_asset.make_sales_invoice",
			callback: function (r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		})
	},

	create_asset_maintenance: function (frm) {
		frappe.call({
			args: {
				"asset": frm.doc.name,
				"item_code": frm.doc.item_code,
				"item_name": frm.doc.item_name,
				"asset_category": frm.doc.asset_category,
				"company": frm.doc.company
			},
			method: "erpnext.controllers.base_asset.create_asset_maintenance",
			callback: function (r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		})
	},

	create_asset_repair: function (frm) {
		frappe.call({
			args: {
				"asset": frm.doc.name,
				"asset_name": frm.doc.asset_name
			},
			method: "erpnext.controllers.base_asset.create_asset_repair",
			callback: function (r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	},

	create_asset_revaluation: function (frm) {
		frappe.call({
			args: {
				"asset": frm.doc.name,
				"asset_category": frm.doc.asset_category,
				"company": frm.doc.company
			},
			method: "erpnext.controllers.base_asset.create_asset_revaluation",
			callback: function (r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	},

	create_depreciation_entry: function (frm) {
		frappe.call({
			method: "erpnext.controllers.base_asset.create_depreciation_entry",
			args: {
				asset_name: frm.doc.name
			},
			callback: function (r) {
				if (r.message) {
					var doclist = frappe.model.sync(r.message);
					frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
				}
			}
		})
	},

	calculate_depreciation: function (frm) {
		frm.trigger("toggle_depreciation_details");
		frm.trigger("toggle_asset_value");
	},

	toggle_depreciation_details: function (frm) {
		frappe.db.get_single_value("Accounts Settings", "enable_finance_books")
			.then((value) => {
				if (value) {
					frm.toggle_reqd("finance_books", (frm.doc.calculate_depreciation && !frm.doc.is_serialized_asset));
					frm.toggle_display("finance_books", (frm.doc.calculate_depreciation && !frm.doc.is_serialized_asset));

					frm.set_df_property("depreciation_template", "hidden", 1);
					frm.set_df_property("depreciation_template", "reqd", 0);
				} else {
					frm.set_df_property("finance_books", "hidden", 1);
					frm.set_df_property("finance_books", "reqd", 0);

					frm.toggle_reqd("depreciation_template", (frm.doc.calculate_depreciation && !frm.doc.is_serialized_asset));
					frm.toggle_display("depreciation_template", (frm.doc.calculate_depreciation && !frm.doc.is_serialized_asset));
				}
			});
	},

	toggle_asset_value: function (frm) {
		frappe.db.get_single_value("Accounts Settings", "enable_finance_books")
			.then((value) => {
				if (value) {
					frm.toggle_display("asset_value", (!frm.doc.calculate_depreciation && !frm.doc.is_serialized_asset));
				} else {
					frm.toggle_display("asset_value", !frm.doc.is_serialized_asset);
				}
			});
	},

	depreciation_template: function (frm) {
		if (frm.doc.depreciation_template) {
			frappe.db.get_value("Depreciation Template", frm.doc.depreciation_template, ["asset_life", "asset_life_unit"], (r) => {
				if (r) {
					if (r.asset_life_unit == "Years") {
						frm.set_value("asset_life_in_months", (r.asset_life * 12));
					} else {
						frm.set_value("asset_life_in_months", r.asset_life);
					}
				}
			});
		}
	},

	depreciation_posting_start_date: function (frm) {
		if (frm.doc.available_for_use_date && frm.doc.depreciation_posting_start_date == frm.doc.available_for_use_date) {
			frappe.msgprint(__("Depreciation Posting Date should not be equal to Available for Use Date."));

			frm.set_value("depreciation_posting_start_date", "");
			frm.refresh_field("depreciation_posting_start_date");
		}
	},

	item_code: function (frm) {
		if (frm.doc.item_code) {
			frappe.db.get_single_value("Accounts Settings", "enable_finance_books")
				.then((value) => {
					if (value) {
						frm.trigger("set_finance_book");
					}
				});
		}
	},

	set_finance_book: function (frm) {
		frappe.call({
			method: "erpnext.controllers.base_asset.get_finance_books",
			args: {
				asset_category: frm.doc.asset_category
			},
			callback: function (r) {
				if (r.message) {
					frm.set_value("finance_books", r.message);
				}
			}
		})
	},

	purchase_receipt: (frm) => {
		frm.trigger("toggle_reference_doc");

		if (frm.doc.purchase_receipt) {
			if (frm.doc.item_code) {
				frappe.db.get_doc("Purchase Receipt", frm.doc.purchase_receipt).then(pr_doc => {
					frm.events.set_values_from_purchase_doc(frm, "Purchase Receipt", pr_doc);
				});
			} else {
				frm.set_value("purchase_receipt", "");
				frappe.msgprint({
					title: __("Not Allowed"),
					message: __("Please select Item Code first")
				});
			}
		}
	},

	purchase_invoice: (frm) => {
		frm.trigger("toggle_reference_doc");

		if (frm.doc.purchase_invoice) {
			if (frm.doc.item_code) {
				frappe.db.get_doc("Purchase Invoice", frm.doc.purchase_invoice).then(pi_doc => {
					frm.events.set_values_from_purchase_doc(frm, "Purchase Invoice", pi_doc);
				});
			} else {
				frm.set_value("purchase_invoice", "");
				frappe.msgprint({
					title: __("Not Allowed"),
					message: __("Please select Item Code first")
				});
			}
		}
	},

	set_values_from_purchase_doc: function (frm, doctype, purchase_doc) {
		frm.set_value("company", purchase_doc.company);
		frm.set_value("purchase_date", purchase_doc.posting_date);

		const item = purchase_doc.items.find(item => item.item_code === frm.doc.item_code);
		if (!item) {
			var doctype_field = frappe.scrub(doctype);
			frm.set_value(doctype_field, "");

			frappe.msgprint({
				title: __("Invalid {0}", [__(doctype)]),
				message: __("The selected {0} does not contain the selected Asset Item.", [__(doctype)]),
				indicator: "red"
			});
		}

		frm.set_value("gross_purchase_amount", item.base_net_rate + item.item_tax_amount);
		item.asset_location && frm.set_value("location", item.asset_location);
		frm.set_value("cost_center", item.cost_center || purchase_doc.cost_center);
	},

	setup_chart: function (frm) {
		var x_intervals = [frm.doc.purchase_date];
		var asset_values = [frm.doc.gross_purchase_amount];
		var last_depreciation_date = frm.doc.purchase_date;

		if (frm.doc.opening_accumulated_depreciation) {
			last_depreciation_date = frappe.datetime.add_months(frm.doc.next_depreciation_date,
				-1 * frm.doc.frequency_of_depreciation);

			x_intervals.push(last_depreciation_date);
			asset_values.push(flt(frm.doc.gross_purchase_amount) -
				flt(frm.doc.opening_accumulated_depreciation));
		}

		$.each(frm.doc.schedules || [], function (i, v) {
			x_intervals.push(v.schedule_date);
			var asset_value = flt(frm.doc.gross_purchase_amount) - flt(v.accumulated_depreciation_amount);

			if (v.journal_entry) {
				last_depreciation_date = v.schedule_date;
				asset_values.push(asset_value);
			} else {
				if (in_list(["Scrapped", "Sold"], frm.doc.status)) {
					asset_values.push(null);
				} else {
					asset_values.push(asset_value);
				}
			}
		});

		if (in_list(["Scrapped", "Sold"], frm.doc.status)) {
			x_intervals.push(frm.doc.disposal_date);
			asset_values.push(0);
			last_depreciation_date = frm.doc.disposal_date;
		}

		frm.dashboard.render_graph({
			title: "Asset Value",
			data: {
				labels: x_intervals,
				datasets: [{
					color: "green",
					values: asset_values,
					formatted: asset_values.map(d => d.toFixed(2))
				}]
			},
			type: "line"
		});
	},

	set_depreciation_rate: function (frm, row) {
		if (row.total_number_of_depreciations && row.frequency_of_depreciation
			&& row.expected_value_after_useful_life) {
			frappe.call({
				method: "get_depreciation_rate",
				doc: frm.doc,
				args: row,
				callback: function (r) {
					if (r.message) {
						frappe.flags.dont_change_rate = true;
						frappe.model.set_value(row.doctype, row.name,
							"rate_of_depreciation", flt(r.message, precision("rate_of_depreciation", row)));
					}
				}
			});
		}
	}
});

frappe.ui.form.on("Asset Finance Book", {
	depreciation_template: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];

		frappe.db.get_value("Depreciation Template", row.depreciation_template, ["asset_life", "asset_life_unit"], (r) => {
			if (r) {
				if (r.asset_life_unit == "Years") {
					row.asset_life_in_months = r.asset_life * 12;
				} else {
					row.asset_life_in_months = r.asset_life;
				}

				frm.refresh_field("finance_books");
			}
		});
	},

	depreciation_method: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		frm.events.set_depreciation_rate(frm, row);
	},

	expected_value_after_useful_life: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		frm.events.set_depreciation_rate(frm, row);
	},

	frequency_of_depreciation: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		frm.events.set_depreciation_rate(frm, row);
	},

	total_number_of_depreciations: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		frm.events.set_depreciation_rate(frm, row);
	},

	rate_of_depreciation: function (frm, cdt, cdn) {
		if (!frappe.flags.dont_change_rate) {
			frappe.model.set_value(cdt, cdn, "expected_value_after_useful_life", 0);
		}

		frappe.flags.dont_change_rate = false;
	},
});

erpnext.asset.scrap_asset = function (frm) {
	frappe.confirm(__("Do you really want to scrap this asset?"), function () {
		frappe.call({
			args: {
				"asset_name": frm.doc.name
			},
			method: "erpnext.assets.doctype.asset.depreciation.scrap_asset",
			callback: function () {
				cur_frm.reload_doc();
			}
		})
	})
};

erpnext.asset.restore_asset = function (frm) {
	frappe.confirm(__("Do you really want to restore this scrapped asset?"), function () {
		frappe.call({
			args: {
				"asset_name": frm.doc.name
			},
			method: "erpnext.assets.doctype.asset.depreciation.restore_asset",
			callback: function () {
				cur_frm.reload_doc();
			}
		})
	})
};
