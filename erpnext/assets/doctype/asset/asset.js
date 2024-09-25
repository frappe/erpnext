// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.asset");
frappe.provide("erpnext.accounts.dimensions");

frappe.ui.form.on("Asset", {
	onload: function (frm) {
		frm.set_query("item_code", function () {
			return {
				filters: {
					is_fixed_asset: 1,
					is_stock_item: 0,
				},
			};
		});

		frm.set_query("warehouse", function () {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0,
				},
			};
		});

		frm.set_query("department", function () {
			return {
				filters: {
					company: frm.doc.company,
				},
			};
		});

		erpnext.accounts.dimensions.setup_dimension_filters(frm, frm.doctype);
	},

	company: function (frm) {
		erpnext.accounts.dimensions.update_dimension(frm, frm.doctype);
	},

	setup: function (frm) {
		frm.ignore_doctypes_on_cancel_all = ["Journal Entry"];

		frm.make_methods = {
			"Asset Movement": () => {
				frappe.call({
					method: "erpnext.assets.doctype.asset.asset.make_asset_movement",
					freeze: true,
					args: {
						assets: [{ name: cur_frm.doc.name }],
					},
					callback: function (r) {
						if (r.message) {
							var doc = frappe.model.sync(r.message)[0];
							frappe.set_route("Form", doc.doctype, doc.name);
						}
					},
				});
			},
		};

		frm.set_query("purchase_receipt", (doc) => {
			return {
				query: "erpnext.controllers.queries.get_purchase_receipts",
				filters: { item_code: doc.item_code },
			};
		});
		frm.set_query("purchase_invoice", (doc) => {
			return {
				query: "erpnext.controllers.queries.get_purchase_invoices",
				filters: { item_code: doc.item_code },
			};
		});
	},

	refresh: function (frm) {
		frappe.ui.form.trigger("Asset", "is_existing_asset");
		frm.toggle_display("next_depreciation_date", frm.doc.docstatus < 1);

		if (frm.doc.docstatus == 1) {
			if (["Submitted", "Partially Depreciated", "Fully Depreciated"].includes(frm.doc.status)) {
				frm.add_custom_button(
					__("Transfer Asset"),
					function () {
						erpnext.asset.transfer_asset(frm);
					},
					__("Manage")
				);

				frm.add_custom_button(
					__("Scrap Asset"),
					function () {
						erpnext.asset.scrap_asset(frm);
					},
					__("Manage")
				);

				frm.add_custom_button(
					__("Sell Asset"),
					function () {
						frm.trigger("make_sales_invoice");
					},
					__("Manage")
				);
			} else if (frm.doc.status == "Scrapped") {
				frm.add_custom_button(
					__("Restore Asset"),
					function () {
						erpnext.asset.restore_asset(frm);
					},
					__("Manage")
				);
			}

			if (frm.doc.maintenance_required && !frm.doc.maintenance_schedule) {
				frm.add_custom_button(
					__("Maintain Asset"),
					function () {
						frm.trigger("create_asset_maintenance");
					},
					__("Manage")
				);
			}

			frm.add_custom_button(
				__("Repair Asset"),
				function () {
					frm.trigger("create_asset_repair");
				},
				__("Manage")
			);

			frm.add_custom_button(
				__("Split Asset"),
				function () {
					frm.trigger("split_asset");
				},
				__("Manage")
			);

			if (frm.doc.status != "Fully Depreciated") {
				frm.add_custom_button(
					__("Adjust Asset Value"),
					function () {
						frm.trigger("create_asset_value_adjustment");
					},
					__("Manage")
				);
			}

			if (!frm.doc.calculate_depreciation) {
				frm.add_custom_button(
					__("Create Depreciation Entry"),
					function () {
						frm.trigger("make_journal_entry");
					},
					__("Manage")
				);
			}

			if (frm.doc.purchase_receipt || !frm.doc.is_existing_asset) {
				frm.add_custom_button(
					__("View General Ledger"),
					function () {
						frappe.route_options = {
							voucher_no: frm.doc.name,
							from_date: frm.doc.available_for_use_date,
							to_date: frm.doc.available_for_use_date,
							company: frm.doc.company,
						};
						frappe.set_route("query-report", "General Ledger");
					},
					__("Manage")
				);
			}

			if (frm.doc.depr_entry_posting_status === "Failed") {
				frm.trigger("set_depr_posting_failure_alert");
			}

			frm.trigger("setup_chart_and_depr_schedule_view");
		}

		frm.trigger("toggle_reference_doc");

		if (frm.doc.docstatus == 0) {
			frm.toggle_reqd("finance_books", frm.doc.calculate_depreciation);

			if (frm.doc.is_composite_asset) {
				frappe.call({
					method: "erpnext.assets.doctype.asset.asset.has_active_capitalization",
					args: {
						asset: frm.doc.name,
					},
					callback: function (r) {
						if (!r.message) {
							$(".primary-action").prop("hidden", true);
							$(".form-message").text("Capitalize this asset to confirm");

							frm.add_custom_button(__("Capitalize Asset"), function () {
								frm.trigger("create_asset_capitalization");
							});
						}
					},
				});
			}
		}
	},

	set_depr_posting_failure_alert: function (frm) {
		const alert = `
			<div class="row">
				<div class="col-xs-12 col-sm-6">
					<span class="indicator whitespace-nowrap red">
						<span>${__("Failed to post depreciation entries")}</span>
					</span>
				</div>
			</div>`;

		frm.dashboard.set_headline_alert(alert);
	},

	toggle_reference_doc: function (frm) {
		if (frm.doc.purchase_receipt && frm.doc.purchase_invoice && frm.doc.docstatus === 1) {
			frm.set_df_property("purchase_invoice", "read_only", 1);
			frm.set_df_property("purchase_receipt", "read_only", 1);
		} else if (frm.doc.is_existing_asset || frm.doc.is_composite_asset) {
			frm.toggle_reqd("purchase_receipt", 0);
			frm.toggle_reqd("purchase_invoice", 0);
		} else if (frm.doc.purchase_receipt) {
			// if purchase receipt link is set then set PI disabled
			frm.toggle_reqd("purchase_invoice", 0);
			frm.set_df_property("purchase_invoice", "read_only", 1);
		} else if (frm.doc.purchase_invoice) {
			// if purchase invoice link is set then set PR disabled
			frm.toggle_reqd("purchase_receipt", 0);
			frm.set_df_property("purchase_receipt", "read_only", 1);
		} else {
			frm.toggle_reqd("purchase_receipt", 1);
			frm.set_df_property("purchase_receipt", "read_only", 0);
			frm.toggle_reqd("purchase_invoice", 1);
			frm.set_df_property("purchase_invoice", "read_only", 0);
		}
	},

	make_journal_entry: function (frm) {
		frappe.call({
			method: "erpnext.assets.doctype.asset.asset.make_journal_entry",
			args: {
				asset_name: frm.doc.name,
			},
			callback: function (r) {
				if (r.message) {
					var doclist = frappe.model.sync(r.message);
					frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
				}
			},
		});
	},

	render_depreciation_schedule_view: function (frm, asset_depr_schedule_doc) {
		let wrapper = $(frm.fields_dict["depreciation_schedule_view"].wrapper).empty();

		let data = [];

		asset_depr_schedule_doc.depreciation_schedule.forEach((sch) => {
			const row = [
				sch["idx"],
				frappe.format(sch["schedule_date"], { fieldtype: "Date" }),
				frappe.format(sch["depreciation_amount"], { fieldtype: "Currency" }),
				frappe.format(sch["accumulated_depreciation_amount"], { fieldtype: "Currency" }),
				sch["journal_entry"] || "",
			];

			if (asset_depr_schedule_doc.shift_based) {
				row.push(sch["shift"]);
			}

			data.push(row);
		});

		let columns = [
			{ name: __("No."), editable: false, resizable: false, format: (value) => value, width: 60 },
			{ name: __("Schedule Date"), editable: false, resizable: false, width: 270 },
			{ name: __("Depreciation Amount"), editable: false, resizable: false, width: 164 },
			{ name: __("Accumulated Depreciation Amount"), editable: false, resizable: false, width: 164 },
		];

		if (asset_depr_schedule_doc.shift_based) {
			columns.push({
				name: __("Journal Entry"),
				editable: false,
				resizable: false,
				format: (value) => `<a href="/app/journal-entry/${value}">${value}</a>`,
				width: 245,
			});
			columns.push({ name: __("Shift"), editable: false, resizable: false, width: 59 });
		} else {
			columns.push({
				name: __("Journal Entry"),
				editable: false,
				resizable: false,
				format: (value) => `<a href="/app/journal-entry/${value}">${value}</a>`,
				width: 304,
			});
		}

		let datatable = new frappe.DataTable(wrapper.get(0), {
			columns: columns,
			data: data,
			layout: "fluid",
			serialNoColumn: false,
			checkboxColumn: true,
			cellHeight: 35,
		});

		datatable.style.setStyle(`.dt-scrollable`, {
			"font-size": "0.75rem",
			"margin-bottom": "1rem",
			"margin-left": "0.35rem",
			"margin-right": "0.35rem",
		});
		datatable.style.setStyle(`.dt-header`, { "margin-left": "0.35rem", "margin-right": "0.35rem" });
		datatable.style.setStyle(`.dt-cell--header .dt-cell__content`, {
			color: "var(--gray-600)",
			"font-size": "var(--text-sm)",
		});
		datatable.style.setStyle(`.dt-cell`, { color: "var(--text-color)" });
		datatable.style.setStyle(`.dt-cell--col-1`, { "text-align": "center" });
		datatable.style.setStyle(`.dt-cell--col-2`, { "font-weight": 600 });
		datatable.style.setStyle(`.dt-cell--col-3`, { "font-weight": 600 });
	},

	setup_chart_and_depr_schedule_view: async function (frm) {
		if (frm.doc.finance_books.length > 1) {
			return;
		}

		var x_intervals = [frappe.format(frm.doc.purchase_date, { fieldtype: "Date" })];
		var asset_values = [frm.doc.gross_purchase_amount];

		if (frm.doc.calculate_depreciation) {
			if (frm.doc.opening_accumulated_depreciation) {
				var depreciation_date = frappe.datetime.add_months(
					frm.doc.finance_books[0].depreciation_start_date,
					-1 * frm.doc.finance_books[0].frequency_of_depreciation
				);
				x_intervals.push(frappe.format(depreciation_date, { fieldtype: "Date" }));
				asset_values.push(
					flt(
						frm.doc.gross_purchase_amount - frm.doc.opening_accumulated_depreciation,
						precision("gross_purchase_amount")
					)
				);
			}

			let asset_depr_schedule_doc = (
				await frappe.call(
					"erpnext.assets.doctype.asset_depreciation_schedule.asset_depreciation_schedule.get_asset_depr_schedule_doc",
					{
						asset_name: frm.doc.name,
						status: "Active",
						finance_book: frm.doc.finance_books[0].finance_book || null,
					}
				)
			).message;

			$.each(asset_depr_schedule_doc.depreciation_schedule || [], function (i, v) {
				x_intervals.push(frappe.format(v.schedule_date, { fieldtype: "Date" }));
				var asset_value = flt(
					frm.doc.gross_purchase_amount - v.accumulated_depreciation_amount,
					precision("gross_purchase_amount")
				);
				if (v.journal_entry) {
					asset_values.push(asset_value);
				} else {
					if (["Scrapped", "Sold"].includes(frm.doc.status)) {
						asset_values.push(null);
					} else {
						asset_values.push(asset_value);
					}
				}
			});

			frm.toggle_display(["depreciation_schedule_view"], 1);
			frm.events.render_depreciation_schedule_view(frm, asset_depr_schedule_doc);
		} else {
			if (frm.doc.opening_accumulated_depreciation) {
				x_intervals.push(frappe.format(frm.doc.creation.split(" ")[0], { fieldtype: "Date" }));
				asset_values.push(
					flt(
						frm.doc.gross_purchase_amount - frm.doc.opening_accumulated_depreciation,
						precision("gross_purchase_amount")
					)
				);
			}

			let depr_entries = (
				await frappe.call({
					method: "get_manual_depreciation_entries",
					doc: frm.doc,
				})
			).message;

			$.each(depr_entries || [], function (i, v) {
				x_intervals.push(frappe.format(v.posting_date, { fieldtype: "Date" }));
				let last_asset_value = asset_values[asset_values.length - 1];
				asset_values.push(flt(last_asset_value - v.value, precision("gross_purchase_amount")));
			});
		}

		if (["Scrapped", "Sold"].includes(frm.doc.status)) {
			x_intervals.push(frappe.format(frm.doc.disposal_date, { fieldtype: "Date" }));
			asset_values.push(0);
		}

		frm.dashboard.render_graph({
			title: "Asset Value",
			data: {
				labels: x_intervals,
				datasets: [
					{
						color: "green",
						values: asset_values,
						formatted: asset_values.map((d) => d?.toFixed(2)),
					},
				],
			},
			type: "line",
		});
	},

	item_code: function (frm) {
		if (frm.doc.item_code && frm.doc.calculate_depreciation && frm.doc.gross_purchase_amount) {
			frm.trigger("set_finance_book");
		} else {
			frm.set_value("finance_books", []);
		}
	},

	set_finance_book: function (frm) {
		frappe.call({
			method: "erpnext.assets.doctype.asset.asset.get_item_details",
			args: {
				item_code: frm.doc.item_code,
				asset_category: frm.doc.asset_category,
				gross_purchase_amount: frm.doc.gross_purchase_amount,
			},
			callback: function (r, rt) {
				if (r.message) {
					frm.set_value("finance_books", r.message);
				}
			},
		});
	},

	is_existing_asset: function (frm) {
		frm.trigger("toggle_reference_doc");
	},

	is_composite_asset: function (frm) {
		if (frm.doc.is_composite_asset) {
			frm.set_value("gross_purchase_amount", 0);
			frm.set_df_property("gross_purchase_amount", "read_only", 1);
		} else {
			frm.set_df_property("gross_purchase_amount", "read_only", 0);
		}

		frm.trigger("toggle_reference_doc");
	},

	make_sales_invoice: function (frm) {
		frappe.call({
			args: {
				asset: frm.doc.name,
				item_code: frm.doc.item_code,
				company: frm.doc.company,
				serial_no: frm.doc.serial_no,
			},
			method: "erpnext.assets.doctype.asset.asset.make_sales_invoice",
			callback: function (r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			},
		});
	},

	create_asset_maintenance: function (frm) {
		frappe.call({
			args: {
				asset: frm.doc.name,
				item_code: frm.doc.item_code,
				item_name: frm.doc.item_name,
				asset_category: frm.doc.asset_category,
				company: frm.doc.company,
			},
			method: "erpnext.assets.doctype.asset.asset.create_asset_maintenance",
			callback: function (r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			},
		});
	},

	create_asset_repair: function (frm) {
		frappe.call({
			args: {
				company: frm.doc.company,
				asset: frm.doc.name,
				asset_name: frm.doc.asset_name,
			},
			method: "erpnext.assets.doctype.asset.asset.create_asset_repair",
			callback: function (r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			},
		});
	},

	create_asset_capitalization: function (frm) {
		frappe.call({
			args: {
				company: frm.doc.company,
				asset: frm.doc.name,
				asset_name: frm.doc.asset_name,
				item_code: frm.doc.item_code,
			},
			method: "erpnext.assets.doctype.asset.asset.create_asset_capitalization",
			callback: function (r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
				$(".primary-action").prop("hidden", false);
			},
		});
	},

	split_asset: function (frm) {
		const title = __("Split Asset");

		const fields = [
			{
				fieldname: "split_qty",
				fieldtype: "Int",
				label: __("Split Qty"),
				reqd: 1,
			},
		];

		let dialog = new frappe.ui.Dialog({
			title: title,
			fields: fields,
		});

		dialog.set_primary_action(__("Split"), function () {
			const dialog_data = dialog.get_values();
			frappe.call({
				args: {
					asset_name: frm.doc.name,
					split_qty: cint(dialog_data.split_qty),
				},
				method: "erpnext.assets.doctype.asset.asset.split_asset",
				callback: function (r) {
					let doclist = frappe.model.sync(r.message);
					frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
				},
			});

			dialog.hide();
		});

		dialog.show();
	},

	create_asset_value_adjustment: function (frm) {
		frappe.call({
			args: {
				asset: frm.doc.name,
				asset_category: frm.doc.asset_category,
				company: frm.doc.company,
			},
			method: "erpnext.assets.doctype.asset.asset.create_asset_value_adjustment",
			freeze: 1,
			callback: function (r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			},
		});
	},

	calculate_depreciation: function (frm) {
		frm.toggle_reqd("finance_books", frm.doc.calculate_depreciation);
		if (frm.doc.item_code && frm.doc.calculate_depreciation && frm.doc.gross_purchase_amount) {
			frm.trigger("set_finance_book");
		} else {
			frm.set_value("finance_books", []);
		}
	},

	gross_purchase_amount: function (frm) {
		if (frm.doc.finance_books) {
			frm.doc.finance_books.forEach((d) => {
				frm.events.set_depreciation_rate(frm, d);
			});
		}
	},

	purchase_receipt: (frm) => {
		frm.trigger("toggle_reference_doc");
		if (frm.doc.purchase_receipt) {
			if (frm.doc.item_code) {
				frappe.db.get_doc("Purchase Receipt", frm.doc.purchase_receipt).then((pr_doc) => {
					frm.events.set_values_from_purchase_doc(frm, "Purchase Receipt", pr_doc);
				});
			} else {
				frm.set_value("purchase_receipt", "");
				frappe.msgprint({
					title: __("Not Allowed"),
					message: __("Please select Item Code first"),
				});
			}
		}
	},

	purchase_invoice: (frm) => {
		frm.trigger("toggle_reference_doc");
		if (frm.doc.purchase_invoice) {
			if (frm.doc.item_code) {
				frappe.db.get_doc("Purchase Invoice", frm.doc.purchase_invoice).then((pi_doc) => {
					frm.events.set_values_from_purchase_doc(frm, "Purchase Invoice", pi_doc);
				});
			} else {
				frm.set_value("purchase_invoice", "");
				frappe.msgprint({
					title: __("Not Allowed"),
					message: __("Please select Item Code first"),
				});
			}
		}
	},

	set_values_from_purchase_doc: function (frm, doctype, purchase_doc) {
		frm.set_value("company", purchase_doc.company);
		if (purchase_doc.bill_date) {
			frm.set_value("purchase_date", purchase_doc.bill_date);
		} else {
			frm.set_value("purchase_date", purchase_doc.posting_date);
		}
		if (!frm.doc.is_existing_asset && !frm.doc.available_for_use_date) {
			frm.set_value("available_for_use_date", frm.doc.purchase_date);
		}
		const item = purchase_doc.items.find((item) => item.item_code === frm.doc.item_code);
		if (!item) {
			let doctype_field = frappe.scrub(doctype);
			frm.set_value(doctype_field, "");
			frappe.msgprint({
				title: __("Invalid {0}", [__(doctype)]),
				message: __("The selected {0} does not contain the selected Asset Item.", [__(doctype)]),
				indicator: "red",
			});
		}
		frappe.db.get_value("Item", item.item_code, "is_grouped_asset", (r) => {
			var asset_quantity = r.is_grouped_asset ? item.qty : 1;
			var purchase_amount = flt(
				item.valuation_rate * asset_quantity,
				precision("gross_purchase_amount")
			);

			frm.set_value("gross_purchase_amount", purchase_amount);
			frm.set_value("purchase_amount", purchase_amount);
			frm.set_value("asset_quantity", asset_quantity);
			frm.set_value("cost_center", item.cost_center || purchase_doc.cost_center);
			if (item.asset_location) {
				frm.set_value("location", item.asset_location);
			}
			if (doctype === "Purchase Receipt") {
				frm.set_value("purchase_receipt_item", item.name);
			} else if (doctype === "Purchase Invoice") {
				frm.set_value("purchase_invoice_item", item.name);
			}
		});
	},

	set_depreciation_rate: function (frm, row) {
		if (
			row.total_number_of_depreciations &&
			row.frequency_of_depreciation &&
			row.expected_value_after_useful_life
		) {
			frappe.call({
				method: "get_depreciation_rate",
				doc: frm.doc,
				args: row,
				callback: function (r) {
					if (r.message) {
						frappe.flags.dont_change_rate = true;
						frappe.model.set_value(
							row.doctype,
							row.name,
							"rate_of_depreciation",
							flt(r.message, precision("rate_of_depreciation", row))
						);
					}
				},
			});
		}
	},

	set_salvage_value_percentage_or_expected_value_after_useful_life: function (
		frm,
		row,
		salvage_value_percentage_changed,
		expected_value_after_useful_life_changed
	) {
		if (expected_value_after_useful_life_changed) {
			frappe.flags.from_set_salvage_value_percentage_or_expected_value_after_useful_life = true;
			const new_salvage_value_percentage = flt(
				(row.expected_value_after_useful_life * 100) / frm.doc.gross_purchase_amount,
				precision("salvage_value_percentage", row)
			);
			frappe.model.set_value(
				row.doctype,
				row.name,
				"salvage_value_percentage",
				new_salvage_value_percentage
			);
			frappe.flags.from_set_salvage_value_percentage_or_expected_value_after_useful_life = false;
		} else if (salvage_value_percentage_changed) {
			frappe.flags.from_set_salvage_value_percentage_or_expected_value_after_useful_life = true;
			const new_expected_value_after_useful_life = flt(
				frm.doc.gross_purchase_amount * (row.salvage_value_percentage / 100),
				precision("gross_purchase_amount")
			);
			frappe.model.set_value(
				row.doctype,
				row.name,
				"expected_value_after_useful_life",
				new_expected_value_after_useful_life
			);
			frappe.flags.from_set_salvage_value_percentage_or_expected_value_after_useful_life = false;
		}
	},
});

frappe.ui.form.on("Asset Finance Book", {
	depreciation_method: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		frm.events.set_depreciation_rate(frm, row);
	},

	expected_value_after_useful_life: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!frappe.flags.from_set_salvage_value_percentage_or_expected_value_after_useful_life) {
			frm.events.set_salvage_value_percentage_or_expected_value_after_useful_life(
				frm,
				row,
				false,
				true
			);
		}
		frm.events.set_depreciation_rate(frm, row);
	},

	salvage_value_percentage: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!frappe.flags.from_set_salvage_value_percentage_or_expected_value_after_useful_life) {
			frm.events.set_salvage_value_percentage_or_expected_value_after_useful_life(
				frm,
				row,
				true,
				false
			);
		}
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

	depreciation_start_date: function (frm, cdt, cdn) {
		const book = locals[cdt][cdn];
		if (frm.doc.available_for_use_date && book.depreciation_start_date < frm.doc.available_for_use_date) {
			frappe.msgprint(__("Depreciation Posting Date cannot be before Available-for-use Date"));
			book.depreciation_start_date = "";
			frm.refresh_field("finance_books");
		}
	},
});

erpnext.asset.scrap_asset = function (frm) {
	frappe.confirm(__("Do you really want to scrap this asset?"), function () {
		frappe.call({
			args: {
				asset_name: frm.doc.name,
			},
			method: "erpnext.assets.doctype.asset.depreciation.scrap_asset",
			callback: function (r) {
				cur_frm.reload_doc();
			},
		});
	});
};

erpnext.asset.restore_asset = function (frm) {
	frappe.confirm(__("Do you really want to restore this scrapped asset?"), function () {
		frappe.call({
			args: {
				asset_name: frm.doc.name,
			},
			method: "erpnext.assets.doctype.asset.depreciation.restore_asset",
			callback: function (r) {
				cur_frm.reload_doc();
			},
		});
	});
};

erpnext.asset.transfer_asset = function () {
	frappe.call({
		method: "erpnext.assets.doctype.asset.asset.make_asset_movement",
		freeze: true,
		args: {
			assets: [{ name: cur_frm.doc.name }],
			purpose: "Transfer",
		},
		callback: function (r) {
			if (r.message) {
				var doc = frappe.model.sync(r.message)[0];
				frappe.set_route("Form", doc.doctype, doc.name);
			}
		},
	});
};
