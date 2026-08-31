// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Blanket Order", {
	onload: function (frm) {
		frm.trigger("set_tc_name_filter");
		if (frm.is_new()) {
			let has_pricing = frm.doc.currency || frm.doc.selling_price_list || frm.doc.buying_price_list;
			blanket_order_pricing.apply(frm, null, { reset_party_values: !has_pricing });
		}
	},

	setup: function (frm) {
		frm.custom_make_buttons = {
			"Purchase Order": "Purchase Order",
			"Sales Order": "Sales Order",
			Quotation: "Quotation",
		};

		frm.add_fetch("customer", "customer_name", "customer_name");
		frm.add_fetch("supplier", "supplier_name", "supplier_name");
		frm.set_query("selling_price_list", () => ({ filters: { selling: 1 } }));
		frm.set_query("buying_price_list", () => ({ filters: { buying: 1 } }));
	},

	refresh: function (frm) {
		erpnext.hide_company(frm);
		blanket_order_pricing.update_labels(frm);
		if (frm.doc.customer && frm.doc.docstatus === 1 && frm.doc.to_date > frappe.datetime.get_today()) {
			frm.add_custom_button(
				__("Sales Order"),
				function () {
					frappe.model.open_mapped_doc({
						method: "erpnext.manufacturing.doctype.blanket_order.blanket_order.make_order",
						frm: frm,
						args: {
							doctype: "Sales Order",
						},
					});
				},
				__("Create")
			);

			frm.add_custom_button(
				__("Quotation"),
				function () {
					frappe.model.open_mapped_doc({
						method: "erpnext.manufacturing.doctype.blanket_order.blanket_order.make_order",
						frm: frm,
						args: {
							doctype: "Quotation",
						},
					});
				},
				__("Create")
			);
		}

		if (frm.doc.supplier && frm.doc.docstatus === 1) {
			frm.add_custom_button(
				__("Purchase Order"),
				function () {
					frappe.model.open_mapped_doc({
						method: "erpnext.manufacturing.doctype.blanket_order.blanket_order.make_order",
						frm: frm,
						args: {
							doctype: "Purchase Order",
						},
					});
				},
				__("Create")
			);
		}
	},

	onload_post_render: function (frm) {
		frm.get_field("items").grid.set_multiple_add("item_code", "qty");
	},

	tc_name: function (frm) {
		erpnext.utils.get_terms(frm.doc.tc_name, frm.doc, function (r) {
			if (!r.exc) {
				frm.set_value("terms", r.message);
			}
		});
	},

	set_tc_name_filter: function (frm) {
		if (frm.doc.blanket_order_type === "Selling") {
			frm.set_df_property("customer", "reqd", 1);
			frm.set_df_property("supplier", "reqd", 0);
			frm.set_value("supplier", "");

			frm.set_query("tc_name", function () {
				return { filters: { selling: 1 } };
			});
		}
		if (frm.doc.blanket_order_type === "Purchasing") {
			frm.set_df_property("supplier", "reqd", 1);
			frm.set_df_property("customer", "reqd", 0);
			frm.set_value("customer", "");

			frm.set_query("tc_name", function () {
				return { filters: { buying: 1 } };
			});
		}
	},

	blanket_order_type: function (frm) {
		frm.trigger("set_tc_name_filter");
		return reset_party_pricing(frm);
	},

	company: reset_party_pricing,

	customer: reset_party_pricing,

	supplier: reset_party_pricing,

	currency: function (frm) {
		return blanket_order_pricing.apply(frm, null, { reset_conversion_rate: true });
	},

	from_date: function (frm) {
		return blanket_order_pricing.apply(frm, null, {
			reset_conversion_rate: true,
			reset_plc_conversion_rate: true,
		});
	},

	conversion_rate: async function (frm) {
		await blanket_order_pricing.update_base_rates(frm);
		return blanket_order_pricing.apply(frm);
	},

	selling_price_list: reset_price_list_exchange_rate,

	buying_price_list: reset_price_list_exchange_rate,

	plc_conversion_rate: function (frm) {
		return blanket_order_pricing.apply(frm);
	},
});

frappe.ui.form.on("Blanket Order Item", {
	item_code: apply_item_pricing,

	qty: apply_item_pricing,

	rate: function (frm, cdt, cdn) {
		return set_base_rate(frm, frappe.get_doc(cdt, cdn));
	},
});

const blanket_order_pricing = {
	update_base_rates(frm) {
		return Promise.all((frm.doc.items || []).map((item) => set_base_rate(frm, item)));
	},

	update_labels(frm) {
		let company_currency = this.get_company_currency(frm);
		let show_base_rate = Boolean(
			frm.doc.currency && company_currency && frm.doc.currency !== company_currency
		);

		frm.set_currency_labels(["price_list_rate", "rate"], frm.doc.currency || company_currency, "items");
		frm.set_currency_labels(["base_price_list_rate", "base_rate"], company_currency, "items");
		frm.fields_dict.items.grid.set_column_disp("base_price_list_rate", show_base_rate);
		frm.fields_dict.items.grid.set_column_disp("base_rate", show_base_rate);
		frm.toggle_display("conversion_rate", show_base_rate);
		frm.toggle_display(
			"plc_conversion_rate",
			Boolean(frm.doc.price_list_currency && frm.doc.price_list_currency !== company_currency)
		);
		frm.set_df_property(
			"conversion_rate",
			"description",
			show_base_rate ? `1 ${frm.doc.currency} = [?] ${company_currency}` : ""
		);
		frm.refresh_fields();
	},

	get_company_currency(frm) {
		return frm.doc.company ? erpnext.get_currency(frm.doc.company) : null;
	},

	async apply(frm, item_name = null, options = {}) {
		if (!frm.doc.company || !frm.doc.blanket_order_type) {
			return;
		}

		if (frm.__applying_blanket_order_price_list) {
			frm.__pending_blanket_order_price_list = { item_name, options };
			return;
		}

		frm.__applying_blanket_order_price_list = true;
		let pending;
		try {
			let response = await frappe.call({
				method: "erpnext.manufacturing.doctype.blanket_order.blanket_order.apply_price_list",
				args: {
					doc: frm.doc,
					item_name,
					reset_party_values: options.reset_party_values,
					reset_conversion_rate: options.reset_conversion_rate,
					reset_plc_conversion_rate: options.reset_plc_conversion_rate,
				},
			});
			if (response.message) {
				await frm.set_value(response.message.parent);
				for (const values of response.message.children) {
					let { name, ...fields } = values;
					let item = (frm.doc.items || []).find((row) => row.name === name);
					if (item) {
						await frappe.model.set_value(item.doctype, item.name, fields);
					}
				}
				this.update_labels(frm);
			}
		} finally {
			frm.__applying_blanket_order_price_list = false;
			pending = frm.__pending_blanket_order_price_list;
			frm.__pending_blanket_order_price_list = null;
		}
		if (pending) {
			return this.apply(frm, pending.item_name, pending.options);
		}
	},
};

function reset_party_pricing(frm) {
	return blanket_order_pricing.apply(frm, null, { reset_party_values: true });
}

function reset_price_list_exchange_rate(frm) {
	return blanket_order_pricing.apply(frm, null, { reset_plc_conversion_rate: true });
}

function apply_item_pricing(frm, cdt, cdn) {
	return blanket_order_pricing.apply(frm, cdn);
}

function set_base_rate(frm, item) {
	frappe.model.round_floats_in(item, ["rate"]);
	let base_rate = flt(flt(item.rate) * flt(frm.doc.conversion_rate), precision("base_rate", item));
	return frappe.model.set_value(item.doctype, item.name, "base_rate", base_rate);
}
