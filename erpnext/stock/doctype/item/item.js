// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.item");

const SALES_DOCTYPES = ["Quotation", "Sales Order", "Delivery Note", "Sales Invoice"];
const PURCHASE_DOCTYPES = ["Purchase Order", "Purchase Receipt", "Purchase Invoice"];

frappe.ui.form.on("Item", {
	valuation_method(frm) {
		if (!frm.is_new() && frm.doc.valuation_method === "Moving Average") {
			let stock_exists = frm.doc.__onload && frm.doc.__onload.stock_exists ? 1 : 0;
			let current_valuation_method = frm.doc.__onload.current_valuation_method;

			if (stock_exists && current_valuation_method !== frm.doc.valuation_method) {
				let msg = __(
					"Changing the valuation method to Moving Average will affect new transactions. If backdated entries are added, earlier FIFO-based entries will be reposted, which may change closing balances."
				);
				msg += "<br><br>";
				msg += __(
					"Also you can't switch back to FIFO after setting the valuation method to Moving Average for this item."
				);
				msg += "<br><br>";
				msg += __("Do you want to change valuation method?");

				frappe.confirm(
					msg,
					() => {
						frm.set_value("valuation_method", "Moving Average");
					},
					() => {
						frm.set_value("valuation_method", current_valuation_method);
					}
				);
			}
		}
	},

	setup: function (frm) {
		frm.add_fetch("attribute", "numeric_values", "numeric_values");
		frm.add_fetch("attribute", "from_range", "from_range");
		frm.add_fetch("attribute", "to_range", "to_range");
		frm.add_fetch("attribute", "increment", "increment");
		frm.add_fetch("tax_type", "tax_rate", "tax_rate");

		frm.make_methods = {
			Quotation: () => {
				open_form(frm, "Quotation", "Quotation Item", "items");
			},
			"Sales Order": () => {
				open_form(frm, "Sales Order", "Sales Order Item", "items");
			},
			"Delivery Note": () => {
				open_form(frm, "Delivery Note", "Delivery Note Item", "items");
			},
			"Sales Invoice": () => {
				open_form(frm, "Sales Invoice", "Sales Invoice Item", "items");
			},
			"Purchase Order": () => {
				open_form(frm, "Purchase Order", "Purchase Order Item", "items");
			},
			"Purchase Receipt": () => {
				open_form(frm, "Purchase Receipt", "Purchase Receipt Item", "items");
			},
			"Purchase Invoice": () => {
				open_form(frm, "Purchase Invoice", "Purchase Invoice Item", "items");
			},
			"Material Request": () => {
				open_form(frm, "Material Request", "Material Request Item", "items");
			},
			"Stock Entry": () => {
				open_form(frm, "Stock Entry", "Stock Entry Detail", "items");
			},
		};
	},

	onload: function (frm) {
		erpnext.item.setup_queries(frm);
		if (frm.doc.variant_of) {
			frm.fields_dict["attributes"].grid.set_column_disp("attribute_value", true);
		}

		if (frm.doc.is_fixed_asset) {
			frm.trigger("set_asset_naming_series");
		}
	},

	toggle_has_serial_batch_fields(frm) {
		let hide_fields = cint(frappe.user_defaults?.enable_serial_and_batch_no_for_item) === 0 ? 1 : 0;

		frm.toggle_display(
			[
				"serial_no_series",
				"batch_number_series",
				"create_new_batch",
				"has_expiry_date",
				"retain_sample",
			],
			!hide_fields
		);
		frm.toggle_enable(["has_serial_no", "has_batch_no"], !hide_fields);

		if (hide_fields) {
			let header = frm.fields_dict["serial_nos_and_batches"].wrapper;
			let wrapper = header.find(".section-head.collapsible");

			render_serial_batch_banner(wrapper);

			if (!wrapper.data("banner-handler-added")) {
				wrapper.data("banner-handler-added", true);

				wrapper.on("click", function () {
					setTimeout(() => {
						let isCollapsed = $(this).hasClass("collapsed");

						wrapper.find(".custom-serial-batch-banner").toggleClass("hidden", isCollapsed);
					}, 10);
				});
			}

			// Button action
			wrapper.find(".go-to-settings").on("click", function () {
				frappe.set_route("Form", "Stock Settings");
			});
		}
	},

	refresh: function (frm) {
		frm.trigger("toggle_has_serial_batch_fields");

		if (frappe.defaults.get_default("item_naming_by") != "Naming Series" || frm.doc.variant_of) {
			frm.toggle_display("naming_series", false);
		} else {
			erpnext.toggle_naming_series();
		}

		frm.toggle_display(["standard_rate"], frappe.model.can_create("Item Price"));

		if (frm.is_new()) {
			frm.toggle_display("disabled", false);
			return;
		}

		frm.toggle_display("disabled", true);

		if (frm.doc.is_stock_item) {
			frm.add_custom_button(
				__("Stock Balance"),
				function () {
					frappe.route_options = {
						item_code: frm.doc.name,
					};
					frappe.set_route("query-report", "Stock Balance");
				},
				__("View")
			);
			frm.add_custom_button(
				__("Stock Ledger"),
				function () {
					frappe.route_options = {
						item_code: frm.doc.name,
					};
					frappe.set_route("query-report", "Stock Ledger");
				},
				__("View")
			);
			frm.add_custom_button(
				__("Stock Projected Qty"),
				function () {
					frappe.route_options = {
						item_code: frm.doc.name,
					};
					frappe.set_route("query-report", "Stock Projected Qty");
				},
				__("View")
			);

			frm.toggle_display(
				["opening_stock"],
				frappe.model.can_create("Stock Entry") && frappe.model.can_write("Stock Entry")
			);
		}

		if (frm.doc.is_fixed_asset) {
			frm.trigger("is_fixed_asset");
			frm.trigger("auto_create_assets");
		}

		// clear intro
		frm.set_intro();

		if (frm.doc.has_variants) {
			frm.set_intro(
				__(
					"This Item is a Template and cannot be used in transactions.<br>All fields present in the 'Copy Fields to Variant' table in Item Variant Settings will be copied to its variant items."
				),
				true
			);

			frm.add_custom_button(
				__("Show Variants"),
				function () {
					frappe.set_route("List", "Item", { variant_of: frm.doc.name });
				},
				__("View")
			);

			frm.add_custom_button(
				__("Item Variant Settings"),
				function () {
					frappe.set_route("Form", "Item Variant Settings");
				},
				__("View")
			);

			frm.add_custom_button(
				__("Variant Details Report"),
				function () {
					frappe.set_route("query-report", "Item Variant Details", { item: frm.doc.name });
				},
				__("View")
			);

			if (frm.doc.variant_based_on === "Item Attribute") {
				frm.add_custom_button(
					__("Single Variant"),
					function () {
						erpnext.item.show_single_variant_dialog(frm);
					},
					__("Create")
				);
				frm.add_custom_button(
					__("Multiple Variants"),
					function () {
						erpnext.item.show_multiple_variants_dialog(frm);
					},
					__("Create")
				);
			} else {
				frm.add_custom_button(
					__("Variant"),
					function () {
						erpnext.item.show_modal_for_manufacturers(frm);
					},
					__("Create")
				);
			}
		}
		if (frm.doc.variant_of) {
			frm.set_intro(
				__("This Item is a Variant of {0} (Template).", [
					`<a href="/app/item/${frm.doc.variant_of}" onclick="location.reload()">${frm.doc.variant_of}</a>`,
				]),
				true
			);
		}

		erpnext.item.toggle_attributes(frm);

		if (!frm.doc.is_fixed_asset) {
			erpnext.item.make_dashboard(frm);
		}

		erpnext.item.render_item_prices(frm);

		frm.add_custom_button(__("Duplicate"), function () {
			var new_item = frappe.model.copy_doc(frm.doc);
			// Duplicate item could have different name, causing "copy paste" error.
			if (new_item.item_name === new_item.item_code) {
				new_item.item_name = null;
			}
			if (new_item.item_code === new_item.description || new_item.item_code === new_item.description) {
				new_item.description = null;
			}
			frappe.set_route("Form", "Item", new_item.name);
		});

		const stock_exists = frm.doc.__onload && frm.doc.__onload.stock_exists ? 1 : 0;

		[
			"is_stock_item",
			"is_customer_provided_item",
			"has_serial_no",
			"has_batch_no",
			"has_variants",
		].forEach((fieldname) => {
			frm.set_df_property(fieldname, "read_only", stock_exists);
		});
		frm.set_df_property("is_fixed_asset", "read_only", frm.doc.__onload?.asset_exists ? 1 : 0);
	},

	validate: function (frm) {
		erpnext.item.weight_to_validate(frm);
	},

	image: function () {
		refresh_field("image_view");
	},

	is_fixed_asset: function (frm) {
		// set serial no to false & toggles its visibility
		frm.set_value("has_serial_no", 0);
		frm.set_value("has_batch_no", 0);
		frm.toggle_enable(["has_serial_no", "serial_no_series"], !frm.doc.is_fixed_asset);

		frappe.call({
			method: "erpnext.stock.doctype.item.item.get_asset_naming_series",
			callback: function (r) {
				frm.set_value("is_stock_item", frm.doc.is_fixed_asset ? 0 : 1);
				frm.events.set_asset_naming_series(frm, r.message);
			},
		});

		frm.trigger("auto_create_assets");
	},

	set_asset_naming_series: function (frm, asset_naming_series) {
		if ((frm.doc.__onload && frm.doc.__onload.asset_naming_series) || asset_naming_series) {
			let naming_series =
				(frm.doc.__onload && frm.doc.__onload.asset_naming_series) || asset_naming_series;
			frm.set_df_property("asset_naming_series", "options", naming_series);
		}
	},

	auto_create_assets: function (frm) {
		frm.toggle_reqd(["asset_naming_series"], frm.doc.auto_create_assets);
		frm.toggle_display(["asset_naming_series"], frm.doc.auto_create_assets);
	},

	page_name: frappe.utils.warn_page_name_change,

	item_code: function (frm) {
		if (!frm.doc.item_name) frm.set_value("item_name", frm.doc.item_code);
	},

	is_stock_item: function (frm) {
		if (!frm.doc.is_stock_item) {
			frm.set_value("has_batch_no", 0);
			frm.set_value("create_new_batch", 0);
			frm.set_value("has_serial_no", 0);
		}
	},

	has_variants: function (frm) {
		erpnext.item.toggle_attributes(frm);
	},
});

frappe.ui.form.on("Item Reorder", {
	reorder_levels_add: function (frm, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		var type = frm.doc.default_material_request_type;
		row.material_request_type = type == "Material Transfer" ? "Transfer" : type;
	},

	warehouse_group(frm, cdt, cdn) {
		let row = locals[cdt][cdn];

		if (!row.warehouse_group) {
			frappe.throw(__("Please select the Warehouse first"));
		}
	},
});

frappe.ui.form.on("Item Customer Detail", {
	customer_items_add: function (frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, "customer_group", "");
	},
	customer_name: function (frm, cdt, cdn) {
		set_customer_group(frm, cdt, cdn);
	},
	customer_group: function (frm, cdt, cdn) {
		if (set_customer_group(frm, cdt, cdn)) {
			frappe.msgprint(__("Changing Customer Group for the selected Customer is not allowed."));
		}
	},
});

var set_customer_group = function (frm, cdt, cdn) {
	var row = frappe.get_doc(cdt, cdn);

	if (!row.customer_name) {
		return false;
	}

	frappe.model.with_doc("Customer", row.customer_name, function () {
		var customer = frappe.model.get_doc("Customer", row.customer_name);
		row.customer_group = customer.customer_group;
		refresh_field("customer_group", cdn, "customer_items");
	});
	return true;
};

function render_serial_batch_banner(wrapper) {
	let hiddenClass = "";
	if (wrapper.hasClass("collapsed")) {
		hiddenClass = "hidden";
	}

	wrapper.find(".custom-serial-batch-banner").remove();

	let banner_html = `
		<div class="custom-serial-batch-banner ${hiddenClass}">
			<div class="banner-content">
				<span class="banner-icon">${frappe.utils.icon("solid-warning", "lg", "", "padding-bottom:2px")}</span>
				<span class="banner-text">
					${__("To use Serial / Batch feature, enable {0} in {1}.", [
						`<b>${__("Activate Serial / Batch No for Item")}</b>`,
						`<a class="go-to-settings" style="text-decoration: underline;">${__(
							"Stock Settings"
						)}</a>`,
					])}
				</span>
			</div>
		</div>
		<style>
			.custom-serial-batch-banner {
				background-color: var(--amber-50);
				border: 1px solid var(--amber-50);
				border-radius: 8px;
				padding: 12px 16px;
				margin-top: 16px;
			}

			.custom-serial-batch-banner .banner-content {
				display: flex;
				align-items: center;
				gap: 12px;
			}

			.custom-serial-batch-banner .banner-icon {
				font-size: 18px;
			}

			.custom-serial-batch-banner .banner-text {
				flex: 1;
				font-size: 14px;
				color: var(--gray-800);
			}

			.custom-serial-batch-banner .btn {
				white-space: nowrap;
			}
		</style>
	`;

	// Insert banner at top of section
	wrapper.append(banner_html);
}

$.extend(erpnext.item, {
	setup_queries: function (frm) {
		frm.fields_dict["item_defaults"].grid.get_field("expense_account").get_query = function (
			doc,
			cdt,
			cdn
		) {
			const row = locals[cdt][cdn];
			return {
				query: "erpnext.controllers.queries.get_expense_account",
				filters: { company: row.company },
			};
		};

		frm.fields_dict["item_defaults"].grid.get_field("income_account").get_query = function (
			doc,
			cdt,
			cdn
		) {
			const row = locals[cdt][cdn];
			return {
				query: "erpnext.controllers.queries.get_income_account",
				filters: { company: row.company },
			};
		};

		frm.fields_dict["item_defaults"].grid.get_field("default_inventory_account").get_query = function (
			doc,
			cdt,
			cdn
		) {
			const row = locals[cdt][cdn];
			return {
				filters: { company: row.company, account_type: "Stock", is_group: 0 },
			};
		};

		frm.fields_dict["item_defaults"].grid.get_field("default_discount_account").get_query = function (
			doc,
			cdt,
			cdn
		) {
			const row = locals[cdt][cdn];
			return {
				filters: {
					report_type: "Profit and Loss",
					company: row.company,
					is_group: 0,
				},
			};
		};

		frm.fields_dict["item_defaults"].grid.get_field("buying_cost_center").get_query = function (
			doc,
			cdt,
			cdn
		) {
			const row = locals[cdt][cdn];
			return {
				filters: {
					is_group: 0,
					company: row.company,
				},
			};
		};

		frm.fields_dict["item_defaults"].grid.get_field("selling_cost_center").get_query = function (
			doc,
			cdt,
			cdn
		) {
			const row = locals[cdt][cdn];
			return {
				filters: {
					is_group: 0,
					company: row.company,
				},
			};
		};

		frm.fields_dict["taxes"].grid.get_field("tax_type").get_query = function (doc, cdt, cdn) {
			return {
				filters: [
					["Account", "account_type", "in", "Tax, Chargeable, Income Account, Expense Account"],
					["Account", "docstatus", "!=", 2],
				],
			};
		};

		frm.fields_dict["item_defaults"].grid.get_field("deferred_revenue_account").get_query = function (
			doc,
			cdt,
			cdn
		) {
			return {
				filters: {
					company: locals[cdt][cdn].company,
					root_type: "Liability",
					is_group: 0,
				},
			};
		};

		frm.fields_dict["item_defaults"].grid.get_field("deferred_expense_account").get_query = function (
			doc,
			cdt,
			cdn
		) {
			return {
				filters: {
					company: locals[cdt][cdn].company,
					root_type: "Asset",
					is_group: 0,
				},
			};
		};

		frm.fields_dict["item_defaults"].grid.get_field("default_warehouse").get_query = function (
			doc,
			cdt,
			cdn
		) {
			const row = locals[cdt][cdn];
			return {
				filters: {
					is_group: 0,
					company: row.company,
				},
			};
		};

		frm.fields_dict.reorder_levels.grid.get_field("warehouse_group").get_query = function (
			doc,
			cdt,
			cdn
		) {
			let row = locals[cdt][cdn];
			return {
				query: "erpnext.stock.doctype.warehouse.warehouse.get_warehouses_for_reorder",
				filters: {
					warehouse: row.warehouse,
				},
			};
		};

		frm.fields_dict.reorder_levels.grid.get_field("warehouse").get_query = function (doc, cdt, cdn) {
			var d = locals[cdt][cdn];

			var filters = {
				is_group: 0,
			};

			if (d.parent_warehouse) {
				filters.extend({ parent_warehouse: d.warehouse_group });
			}

			return {
				filters: filters,
			};
		};

		frm.set_query("default_provisional_account", "item_defaults", (doc, cdt, cdn) => {
			let row = locals[cdt][cdn];
			return {
				filters: {
					company: row.company,
					root_type: ["in", ["Liability", "Asset"]],
					is_group: 0,
				},
			};
		});

		let fields = [
			"purchase_expense_account",
			"purchase_expense_contra_account",
			"expenses_added_to_stock_account",
			"expenses_added_to_stock_contra_account",
			"default_cogs_account",
		];

		fields.forEach((field) => {
			frm.set_query(field, "item_defaults", (doc, cdt, cdn) => {
				let row = locals[cdt][cdn];
				return {
					filters: {
						company: row.company,
						root_type: "Expense",
						is_group: 0,
					},
				};
			});
		});

		frm.set_query("default_inventory_account", "item_defaults", (doc, cdt, cdn) => {
			let row = locals[cdt][cdn];
			return {
				filters: {
					is_group: 0,
					company: row.company,
					account_type: "Stock",
				},
			};
		});
	},

	make_dashboard: function (frm) {
		if (frm.doc.__islocal) return;

		if (frm.doc.is_stock_item) {
			frappe.require("item-dashboard.bundle.js", function () {
				const section = frm.fields_dict["stock_levels_html"].$wrapper;

				erpnext.item.item_dashboard = new erpnext.stock.ItemDashboard({
					parent: section,
					item_code: frm.doc.name,
					page_length: 20,
					method: "erpnext.stock.dashboard.item_dashboard.get_data",
					template: "item_dashboard_list",
				});
				erpnext.item.item_dashboard.refresh();
			});
		}
	},

	render_item_prices: function (frm) {
		if (frm.doc.__islocal) return;

		if (!frappe.model.can_read("Item Price")) {
			frm.toggle_display("prices_html", false);
			return;
		}
		frm.toggle_display("prices_html", true);

		const requested_item = frm.doc.name;
		const container = frm.fields_dict["prices_html"].$wrapper;

		container.html(
			`<div class="text-muted text-center" style="padding: 20px;">${__("Loading...")}</div>`
		);

		frappe.call({
			method: "erpnext.stock.doctype.item.item.get_item_prices",
			args: { item_code: requested_item },

			callback: function (r) {
				if (requested_item !== frm.doc.name) return;

				if (!r.message) return;

				const { prices, has_more } = r.message;

				const html = frappe.render_template("item_prices", {
					prices,
					has_more,
					item_code: requested_item,
					stock_uom: frm.doc.stock_uom,
				});

				container.html(html);

				container.find(".add-price-btn").on("click", () => {
					const filters = {};
					if (frm.doc.is_sales_item && !frm.doc.is_purchase_item) {
						filters.selling = 1;
					} else if (frm.doc.is_purchase_item && !frm.doc.is_sales_item) {
						filters.buying = 1;
					}
					frappe.new_doc(
						"Item Price",
						{ item_code: requested_item, uom: frm.doc.stock_uom },
						(dialog) => {
							if (Object.keys(filters).length) {
								dialog.fields_dict.price_list.get_query = () => ({ filters });
							}
						}
					);
				});

				container.find(".price-row").on("click", function (e) {
					if ($(e.target).is("a")) return;

					frappe.set_route("Form", "Item Price", $(this).data("name"));
				});
			},
		});
	},

	weight_to_validate: function (frm) {
		if (frm.doc.weight_per_unit && !frm.doc.weight_uom) {
			frappe.msgprint({
				message: __("Please mention 'Weight UOM' along with Weight."),
				title: __("Note"),
			});
		}
	},

	show_modal_for_manufacturers: function (frm) {
		var dialog = new frappe.ui.Dialog({
			fields: [
				{
					fieldtype: "Link",
					fieldname: "manufacturer",
					options: "Manufacturer",
					label: "Manufacturer",
					reqd: 1,
				},
				{
					fieldtype: "Data",
					label: "Manufacturer Part Number",
					fieldname: "manufacturer_part_no",
				},
			],
		});

		dialog.set_primary_action(__("Create"), function () {
			var data = dialog.get_values();
			if (!data) return;

			// call the server to make the variant
			data.template = frm.doc.name;
			frappe.call({
				method: "erpnext.controllers.item_variant.get_variant",
				args: data,
				callback: function (r) {
					var doclist = frappe.model.sync(r.message);
					dialog.hide();
					frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
				},
			});
		});

		dialog.show();
	},

	show_multiple_variants_dialog: function (frm) {
		var me = this;

		let promises = [];
		let attr_val_fields = {};

		function make_fields_from_attribute_values(attr_dict) {
			let fields = [];
			let attributes = frm.doc.attributes.filter((row) => !row.disabled);
			attributes.forEach((row, i) => {
				let name = row.attribute;
				if (i % 3 === 0) {
					fields.push({ fieldtype: "Section Break" });
				}
				fields.push({ fieldtype: "Column Break" });
				fields.push({
					fieldtype: "MultiSelectPills",
					label: name,
					fieldname: frappe.scrub(name),
					placeholder: __("Search values..."),
					get_data: (txt) => get_attribute_suggestions(attr_dict[name], txt),
					onchange: update_primary_action,
				});
			});
			return fields;
		}

		function get_attribute_suggestions(spec, txt) {
			if (!spec) return [];
			return Array.isArray(spec) ? filter_list(spec, txt) : numeric_suggestions(spec, txt);
		}

		// Cap matches so a long value list never hands everything to Awesomplete,
		// which would freeze the browser.
		function filter_list(values, txt) {
			txt = (txt || "").toLowerCase();
			let matches = [];
			for (let value of values) {
				if (!txt || value.toLowerCase().includes(txt)) {
					matches.push(value);
					if (matches.length >= 50) break;
				}
			}
			return matches;
		}

		// Numeric ranges aren't enumerated. With no input, preview the first few
		// values; once the user types, accept it only if it lies on the increment
		// within [from, to]. Both paths are cheap even for huge ranges.
		function numeric_suggestions(range, txt) {
			let { from_range: from, to_range: to, increment } = range;
			if (!(increment > 0) || from > to) return [];

			txt = (txt || "").trim();
			if (!txt) {
				let preview = [];
				for (
					let value = from;
					value <= to && preview.length < 50;
					value = flt(value + increment, 6)
				) {
					preview.push(String(value));
				}
				return preview;
			}

			return is_valid_attribute_value(range, txt) ? [String(flt(txt, 6))] : [];
		}

		function is_valid_attribute_value(spec, value) {
			if (!spec || !value) return false;
			if (Array.isArray(spec)) return spec.includes(value);

			let { from_range: from, to_range: to, increment } = spec;
			if (!(increment > 0)) return false;

			// Reject anything that isn't cleanly a number ("abc", "5000xyz", "");
			// flt would coerce these to 0 and wrongly accept them.
			let text = String(value).trim();
			let num = Number(text);
			if (text === "" || !Number.isFinite(num)) return false;

			if (num < from || num > to) return false;
			let steps = (num - from) / increment;
			return Math.abs(Math.round(steps) - steps) <= 1e-6;
		}

		// Block variant creation if anything is wrong: an invalid committed pill, or
		// text typed but not added as a pill (which get_selected_attributes would
		// otherwise drop silently). The user must fix each before creation proceeds.
		function validate_selected_attributes() {
			let errors = [];
			frm.doc.attributes.forEach((row) => {
				if (row.disabled) return;
				let field = me.multiple_variant_dialog.get_field(frappe.scrub(row.attribute));
				if (!field) return;

				let attribute = frappe.utils.escape_html(row.attribute);
				let spec = attr_val_fields[row.attribute];

				let invalid = [
					...new Set((field.get_value() || []).filter((v) => !is_valid_attribute_value(spec, v))),
				];
				if (invalid.length) {
					let values = invalid.map(frappe.utils.escape_html).join(", ");
					errors.push(__("{0}: remove invalid value(s) {1}", [attribute, values]));
				}

				let pending = (field.$input?.val() || "").trim();
				if (pending) {
					let value = frappe.utils.escape_html(pending);
					errors.push(
						__("{0}: select the typed value {1} from the list or clear it", [attribute, value])
					);
				}
			});

			if (errors.length) {
				frappe.throw({
					title: __("Invalid Attribute Values"),
					message: errors.join("<br>"),
					indicator: "red",
				});
			}
		}

		function update_primary_action() {
			let selected_attributes = get_selected_attributes();
			let counts = Object.keys(selected_attributes).map((key) => selected_attributes[key].length);
			if (!counts.length) {
				me.multiple_variant_dialog.get_primary_btn().html(__("Create Variants"));
				me.multiple_variant_dialog.disable_primary_action();
			} else {
				let no_of_combinations = counts.reduce((a, b) => a * b, 1);
				let msg =
					no_of_combinations === 1
						? __("Make {0} Variant", [no_of_combinations])
						: __("Make {0} Variants", [no_of_combinations]);
				me.multiple_variant_dialog.get_primary_btn().html(msg);
				me.multiple_variant_dialog.enable_primary_action();
			}
		}

		function make_and_show_dialog(fields) {
			me.multiple_variant_dialog = new frappe.ui.Dialog({
				title: __("Select Attribute Values"),
				fields: [
					frm.doc.image
						? {
								fieldtype: "Check",
								label: __("Create a variant with the template image."),
								fieldname: "use_template_image",
								default: 0,
						  }
						: null,
					{
						fieldtype: "HTML",
						fieldname: "help",
						options: `<label class="control-label">
							${__("Select at least one attribute value.")}
						</label>`,
					},
				]
					.concat(fields)
					.filter(Boolean),
			});

			me.multiple_variant_dialog.set_primary_action(__("Create Variants"), () => {
				validate_selected_attributes();

				let selected_attributes = get_selected_attributes();
				let use_template_image = me.multiple_variant_dialog.get_value("use_template_image");

				me.multiple_variant_dialog.hide();
				frappe.call({
					method: "erpnext.controllers.item_variant.enqueue_multiple_variant_creation",
					args: {
						item: frm.doc.name,
						args: selected_attributes,
						use_template_image: use_template_image,
					},
					callback: function (r) {
						if (r.message === "queued") {
							frappe.show_alert({
								message: __("Variant creation has been queued."),
								indicator: "orange",
							});
						} else {
							frappe.show_alert({
								message: __("{0} variants created.", [r.message]),
								indicator: "green",
							});
						}
					},
				});
			});

			me.multiple_variant_dialog.disable_primary_action();
			me.multiple_variant_dialog.clear();
			me.multiple_variant_dialog.show();
		}

		function get_selected_attributes() {
			let selected_attributes = {};
			frm.doc.attributes.forEach((row) => {
				if (row.disabled) return;
				let values = me.multiple_variant_dialog.get_value(frappe.scrub(row.attribute));
				if (values && values.length) {
					selected_attributes[row.attribute] = values;
				}
			});
			return selected_attributes;
		}

		frm.doc.attributes.forEach(function (d) {
			if (!d.disabled) {
				let p = new Promise((resolve) => {
					// Read the numeric configuration from the Item Attribute master
					// instead of the variant attribute row, which may be stale or
					// blank if the attribute was made numeric after it was added here.
					frappe.db
						.get_value("Item Attribute", d.attribute, [
							"numeric_values",
							"from_range",
							"to_range",
							"increment",
						])
						.then((res) => {
							let attr = res.message || {};

							if (!attr.numeric_values) {
								frappe
									.call({
										method: "frappe.client.get_list",
										args: {
											doctype: "Item Attribute Value",
											filters: [["parent", "=", d.attribute]],
											fields: ["attribute_value"],
											limit_page_length: 0,
											parent: "Item Attribute",
											order_by: "idx",
										},
									})
									.then((r) => {
										attr_val_fields[d.attribute] = (r.message || []).map(
											(row) => row.attribute_value
										);
										resolve();
									});
							} else {
								// Store the range instead of enumerating it; a large range
								// (e.g. 1-100000) is slow to build and to search. Values are
								// validated against the range on demand while typing.
								attr_val_fields[d.attribute] = {
									from_range: flt(attr.from_range),
									to_range: flt(attr.to_range),
									increment: flt(attr.increment),
								};
								resolve();
							}
						});
				});

				promises.push(p);
			}
		}, this);

		Promise.all(promises).then(() => {
			let fields = make_fields_from_attribute_values(attr_val_fields);
			make_and_show_dialog(fields);
		});
	},

	show_single_variant_dialog: function (frm) {
		var fields = [];

		for (var i = 0; i < frm.doc.attributes.length; i++) {
			var fieldtype, desc;
			var row = frm.doc.attributes[i];

			if (!row.disabled) {
				if (row.numeric_values) {
					const all_are_int =
						flt(row.from_range) === cint(row.from_range) &&
						flt(row.to_range) === cint(row.to_range) &&
						flt(row.increment) === cint(row.increment);
					fieldtype = all_are_int ? "Int" : "Float";
					const df = { fieldtype };
					const options = all_are_int ? { inline: 1 } : { always_show_decimals: true, inline: 1 };
					desc = __("Min Value: {0}, Max Value: {1}, in Increments of: {2}", [
						frappe.format(row.from_range, df, options),
						frappe.format(row.to_range, df, options),
						frappe.format(row.increment, df, options),
					]);
				} else {
					fieldtype = "Data";
					desc = "";
				}
				fields = fields.concat({
					label: row.attribute,
					fieldname: row.attribute,
					fieldtype: fieldtype,
					reqd: 0,
					description: desc,
				});
			}
		}

		if (frm.doc.image) {
			fields.push({
				fieldtype: "Check",
				label: __("Create a variant with the template image."),
				fieldname: "use_template_image",
				default: 0,
			});
		}

		var d = new frappe.ui.Dialog({
			title: __("Create Variant"),
			fields: fields,
		});

		d.set_primary_action(__("Create"), function () {
			var args = d.get_values();
			if (!args) return;
			frappe.call({
				method: "erpnext.controllers.item_variant.get_variant",
				btn: d.get_primary_btn(),
				args: {
					template: frm.doc.name,
					args: d.get_values(),
				},
				callback: function (r) {
					// returns variant item
					if (r.message) {
						var variant = r.message;
						frappe.msgprint_dialog = frappe.msgprint(
							__("Item Variant {0} already exists with same attributes", [
								repl(
									'<a href="/app/item/%(item_encoded)s" class="strong variant-click">%(item)s</a>',
									{
										item_encoded: encodeURIComponent(variant),
										item: variant,
									}
								),
							])
						);
						frappe.msgprint_dialog.hide_on_page_refresh = true;
						frappe.msgprint_dialog.$wrapper.find(".variant-click").on("click", function () {
							d.hide();
						});
					} else {
						d.hide();
						frappe.call({
							method: "erpnext.controllers.item_variant.create_variant",
							args: {
								item: frm.doc.name,
								args: d.get_values(),
								use_template_image: args.use_template_image,
							},
							callback: function (r) {
								var doclist = frappe.model.sync(r.message);
								frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
							},
						});
					}
				},
			});
		});

		d.show();

		$.each(d.fields_dict, function (i, field) {
			if (field.df.fieldtype !== "Data") {
				return;
			}

			$(field.input_area).addClass("ui-front");

			var input = field.$input.get(0);
			input.awesomplete = new Awesomplete(input, {
				minChars: 0,
				maxItems: 99,
				autoFirst: true,
				list: [],
			});
			input.field = field;

			field.$input
				.on("input", function (e) {
					var term = e.target.value;
					frappe.call({
						method: "erpnext.stock.doctype.item.item.get_item_attribute",
						args: {
							parent: i,
							attribute_value: term,
						},
						callback: function (r) {
							if (r.message) {
								e.target.awesomplete.list = r.message.map(function (d) {
									return d.attribute_value;
								});
							}
						},
					});
				})
				.on("focus", function (e) {
					$(e.target).val("").trigger("input");
				})
				.on("awesomplete-open", () => {
					let modal = field.$input.parents(".modal-dialog")[0];
					if (modal) {
						$(modal).removeClass("modal-dialog-scrollable");
					}
				});
		});
	},

	toggle_attributes: function (frm) {
		if ((frm.doc.has_variants || frm.doc.variant_of) && frm.doc.variant_based_on === "Item Attribute") {
			frm.toggle_display("attributes", true);

			var grid = frm.fields_dict.attributes.grid;

			if (frm.doc.variant_of) {
				// variant

				// value column is displayed but not editable
				grid.set_column_disp("attribute_value", true);
				grid.toggle_enable("attribute_value", false);

				grid.toggle_enable("attribute", false);

				// can't change attributes since they are
				// saved when the variant was created
				frm.toggle_enable("attributes", false);
			} else {
				// template - values not required!

				// make the grid editable
				frm.toggle_enable("attributes", true);

				// value column is hidden
				grid.set_column_disp("attribute_value", false);

				// enable the grid so you can add more attributes
				grid.toggle_enable("attribute", true);
			}
		} else {
			// nothing to do with attributes, hide it
			frm.toggle_display("attributes", false);
		}
		frm.layout.refresh_sections();
	},
});

frappe.ui.form.on("UOM Conversion Detail", {
	uom: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.uom) {
			frappe.call({
				method: "erpnext.stock.doctype.item.item.get_uom_conv_factor",
				args: {
					uom: row.uom,
					stock_uom: frm.doc.stock_uom,
				},
				callback: function (r) {
					if (!r.exc && r.message) {
						frappe.model.set_value(cdt, cdn, "conversion_factor", r.message);
					}
				},
			});
		}
	},
});

frappe.tour["Item"] = [
	{
		fieldname: "item_code",
		title: "Item Code",
		description: __(
			"Enter an Item Code, the name will be auto-filled the same as Item Code on clicking inside the Item Name field."
		),
	},
	{
		fieldname: "item_group",
		title: "Item Group",
		description: __("Select an Item Group."),
	},
	{
		fieldname: "is_stock_item",
		title: "Maintain Stock",
		description: __(
			"If you are maintaining stock of this Item in your Inventory, ERPNext will make a stock ledger entry for each transaction of this item."
		),
	},
	{
		fieldname: "include_item_in_manufacturing",
		title: "Include Item in Manufacturing",
		description: __(
			"This is for raw material Items that'll be used to create finished goods. If the Item is an additional service like 'washing' that'll be used in the BOM, keep this unchecked."
		),
	},
	{
		fieldname: "opening_stock",
		title: "Opening Stock",
		description: __("Enter the opening stock units."),
	},
	{
		fieldname: "valuation_rate",
		title: "Valuation Rate",
		description: __(
			"There are two options to maintain valuation of stock. FIFO (first in - first out) and Moving Average. To understand this topic in detail please visit <a href='https://docs.frappe.io/erpnext/user/manual/en/calculation-of-valuation-rate-in-fifo-and-moving-average' target='_blank'>Item Valuation, FIFO and Moving Average.</a>"
		),
	},
	{
		fieldname: "standard_rate",
		title: "Standard Selling Rate",
		description: __(
			"When creating an Item, entering a value for this field will automatically create an Item Price at the backend."
		),
	},
	{
		fieldname: "item_defaults",
		title: "Item Defaults",
		description: __(
			"In this section, you can define Company-wide transaction-related defaults for this Item. Eg. Default Warehouse, Default Price List, Supplier, etc."
		),
	},
];

function open_form(frm, doctype, child_doctype, parentfield) {
	frappe.model.with_doctype(doctype, () => {
		let new_doc = frappe.model.get_new_doc(doctype);

		let new_child_doc = frappe.model.add_child(new_doc, child_doctype, parentfield);
		new_child_doc.item_code = frm.doc.name;
		new_child_doc.item_name = frm.doc.item_name;
		if (SALES_DOCTYPES.includes(doctype) && frm.doc.sales_uom) {
			new_child_doc.uom = frm.doc.sales_uom;
		} else if (PURCHASE_DOCTYPES.includes(doctype) && frm.doc.purchase_uom) {
			new_child_doc.uom = frm.doc.purchase_uom;
		} else {
			new_child_doc.uom = frm.doc.stock_uom;
		}
		new_child_doc.description = frm.doc.description;
		if (!new_child_doc.qty) {
			new_child_doc.qty = 1.0;
		}

		frappe.run_serially([
			() => frappe.ui.form.make_quick_entry(doctype, null, null, new_doc),
			() => {
				frappe.flags.ignore_company_party_validation = true;
				frappe.model.trigger("item_code", frm.doc.name, new_child_doc);
			},
		]);
	});
}
