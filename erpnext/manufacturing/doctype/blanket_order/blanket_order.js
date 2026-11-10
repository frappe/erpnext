// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

const BLANKET_ORDER_SELLING_ADDRESS_FIELDS = [
	"customer_address",
	"customer_address_display",
	"contact_person",
	"contact_display",
	"contact_phone",
	"contact_mobile",
	"contact_email",
	"shipping_address_name",
	"shipping_address",
	"dispatch_address_name",
	"dispatch_address",
	"company_address",
	"company_address_display",
	"company_contact_person",
];

const BLANKET_ORDER_PURCHASING_ADDRESS_FIELDS = [
	"supplier_address",
	"supplier_address_display",
	"contact_person",
	"contact_display",
	"contact_phone",
	"contact_mobile",
	"contact_email",
	"shipping_address_name",
	"shipping_address",
	"company_address",
	"company_address_display",
];

frappe.ui.form.on("Blanket Order", {
	onload: function (frm) {
		frm.trigger("set_tc_name_filter");
		frm.trigger("set_dynamic_link");
		if (frm.is_new()) {
			let has_pricing = frm.doc.currency || frm.doc.selling_price_list || frm.doc.buying_price_list;
			blanket_order_pricing.apply(frm, null, { reset_party_values: !has_pricing });
		}
	},

	setup: function (frm) {
		frm.set_indicator_formatter("item_code", function (doc) {
			if (doc.closed) {
				return "gray";
			}
			return flt(doc.ordered_qty) >= flt(doc.stock_qty) ? "green" : "orange";
		});

		frm.custom_make_buttons = {
			"Purchase Order": "Purchase Order",
			"Sales Order": "Sales Order",
			Quotation: "Quotation",
		};

		frm.add_fetch("customer", "customer_name", "customer_name");
		frm.add_fetch("supplier", "supplier_name", "supplier_name");
		frm.set_query("selling_price_list", () => ({ filters: { selling: 1 } }));
		frm.set_query("buying_price_list", () => ({ filters: { buying: 1 } }));

		frm.set_query("contact_person", erpnext.queries.contact_query);
		frm.set_query("company_contact_person", erpnext.queries.company_contact_query);
		frm.set_query("customer_address", erpnext.queries.address_query);
		frm.set_query("supplier_address", erpnext.queries.address_query);
		frm.set_query("dispatch_address_name", erpnext.queries.dispatch_address_query);
		frm.set_query("company_address", erpnext.queries.company_address_query);
		frm.set_query("shipping_address_name", () => {
			if (frm.doc.blanket_order_type === "Selling" && frm.doc.customer) {
				return {
					query: "frappe.contacts.doctype.address.address.address_query",
					filters: { link_doctype: "Customer", link_name: frm.doc.customer },
				};
			}
			return erpnext.queries.company_address_query(frm.doc);
		});
	},

	refresh: function (frm) {
		erpnext.hide_company(frm);
		blanket_order_pricing.update_labels(frm);
		add_blanket_order_status_buttons(frm);
		erpnext.item_close.add_buttons(frm, get_blanket_order_item_close_config());
		if (frm.doc.status === "Closed") {
			return;
		}

		const can_order = frm.doc.docstatus === 1 && frm.doc.to_date >= frappe.datetime.get_today();

		if (frm.doc.customer && can_order) {
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

		if (frm.doc.supplier && can_order) {
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
			if (frm.doc.supplier) {
				frm.set_value("supplier", "");
			}

			frm.set_query("tc_name", function () {
				return { filters: { selling: 1, disabled: 0 } };
			});
		}
		if (frm.doc.blanket_order_type === "Purchasing") {
			frm.set_df_property("supplier", "reqd", 1);
			frm.set_df_property("customer", "reqd", 0);
			if (frm.doc.customer) {
				frm.set_value("customer", "");
			}

			frm.set_query("tc_name", function () {
				return { filters: { buying: 1, disabled: 0 } };
			});
		}
	},

	blanket_order_type: function (frm) {
		frm.trigger("set_tc_name_filter");
		frm.trigger("set_dynamic_link");
		frm.trigger("clear_address_and_contact");
		return reset_party_pricing(frm);
	},

	company: function (frm) {
		frm.trigger("set_party_address_details");
		return reset_party_pricing(frm);
	},

	customer: function (frm) {
		frm.trigger("set_dynamic_link");
		frm.trigger("set_party_address_details");
		return reset_party_pricing(frm);
	},

	supplier: function (frm) {
		frm.trigger("set_dynamic_link");
		frm.trigger("set_party_address_details");
		return reset_party_pricing(frm);
	},

	customer_address: function (frm) {
		erpnext.utils.get_address_display(frm, "customer_address", "customer_address_display");
	},

	supplier_address: function (frm) {
		erpnext.utils.get_address_display(frm, "supplier_address", "supplier_address_display");
	},

	shipping_address_name: function (frm) {
		erpnext.utils.get_address_display(frm, "shipping_address_name", "shipping_address");
	},

	dispatch_address_name: function (frm) {
		erpnext.utils.get_address_display(frm, "dispatch_address_name", "dispatch_address");
	},

	company_address: function (frm) {
		erpnext.utils.get_address_display(frm, "company_address", "company_address_display", true);
	},

	contact_person: function (frm) {
		erpnext.utils.get_contact_details(frm);
	},

	set_dynamic_link: function (frm) {
		if (frm.doc.blanket_order_type === "Selling" && frm.doc.customer) {
			frappe.dynamic_link = { doc: frm.doc, fieldname: "customer", doctype: "Customer" };
		} else if (frm.doc.blanket_order_type === "Purchasing" && frm.doc.supplier) {
			frappe.dynamic_link = { doc: frm.doc, fieldname: "supplier", doctype: "Supplier" };
		}
	},

	clear_address_and_contact: function (frm) {
		const fields =
			frm.doc.blanket_order_type === "Selling"
				? BLANKET_ORDER_PURCHASING_ADDRESS_FIELDS
				: BLANKET_ORDER_SELLING_ADDRESS_FIELDS;
		const update = {};
		fields.forEach((field) => {
			update[field] = "";
		});
		frm.set_value(update);
	},

	set_party_address_details: function (frm) {
		const party = frm.doc.blanket_order_type === "Selling" ? frm.doc.customer : frm.doc.supplier;
		if (!party || !frm.doc.company) {
			return;
		}

		const party_type = frm.doc.blanket_order_type === "Selling" ? "Customer" : "Supplier";
		const reference_doctype = frm.doc.blanket_order_type === "Selling" ? "Sales Order" : "Purchase Order";

		frappe.call({
			method: "erpnext.accounts.party.get_party_details",
			args: {
				party,
				party_type,
				company: frm.doc.company,
				doctype: reference_doctype,
				fetch_payment_terms_template: 0,
			},
			callback(r) {
				if (!r.message) {
					return;
				}

				const update =
					frm.doc.blanket_order_type === "Selling"
						? {
								customer_address: r.message.customer_address,
								customer_address_display: r.message.address_display,
								contact_person: r.message.contact_person,
								contact_display: r.message.contact_display,
								contact_phone: r.message.contact_phone,
								contact_mobile: r.message.contact_mobile,
								contact_email: r.message.contact_email,
								shipping_address_name: r.message.shipping_address_name,
								shipping_address: r.message.shipping_address,
								dispatch_address_name: r.message.dispatch_address_name,
								dispatch_address: r.message.dispatch_address,
								company_address: r.message.company_address,
								company_address_display: r.message.company_address_display,
								company_contact_person: r.message.company_contact_person,
						  }
						: {
								supplier_address: r.message.supplier_address,
								supplier_address_display: r.message.address_display,
								contact_person: r.message.contact_person,
								contact_display: r.message.contact_display,
								contact_phone: r.message.contact_phone,
								contact_mobile: r.message.contact_mobile,
								contact_email: r.message.contact_email,
								shipping_address_name: r.message.shipping_address,
								shipping_address: r.message.shipping_address_display,
								company_address: r.message.billing_address,
								company_address_display: r.message.billing_address_display,
						  };
				frm.set_value(update);
			},
		});
	},

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
	item_code: function (frm, cdt, cdn) {
		locals[cdt][cdn].uom = "";
		locals[cdt][cdn].conversion_factor = 0;
		return apply_item_pricing(frm, cdt, cdn);
	},

	uom: function (frm, cdt, cdn) {
		if (frm.__applying_blanket_order_price_list) {
			return;
		}
		return apply_item_pricing(frm, cdt, cdn);
	},

	qty: function (frm, cdt, cdn) {
		calculate_stock_qty(cdt, cdn);
		return apply_item_pricing(frm, cdt, cdn);
	},

	conversion_factor: function (frm, cdt, cdn) {
		return calculate_stock_qty(cdt, cdn);
	},

	rate: function (frm, cdt, cdn) {
		calculate_stock_uom_rate(cdt, cdn);
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

function add_blanket_order_status_buttons(frm) {
	if (frm.doc.docstatus !== 1 || !frm.has_perm("submit")) {
		return;
	}

	if (frm.doc.status === "Closed") {
		frm.add_custom_button(
			__("Re-open"),
			() => update_blanket_order_status(frm, "Submitted"),
			__("Status")
		);
	} else {
		frm.add_custom_button(__("Close"), () => update_blanket_order_status(frm, "Closed"), __("Status"));
	}
}

function get_blanket_order_item_close_config() {
	return {
		is_closable: (item) => !item.closed && flt(item.ordered_qty) < flt(item.stock_qty),
		help: __(
			"Closed rows can no longer be ordered. They are skipped when creating an order from this Blanket Order."
		),
		summarise: (item) => ({
			item_code: item.item_code,
			item_name: item.item_name,
			qty: item.stock_qty,
			ordered_qty: item.ordered_qty || 0,
			pending_qty: Math.max(flt(item.stock_qty) - flt(item.ordered_qty), 0),
			stock_uom: item.stock_uom,
		}),
		columns: [
			erpnext.item_close.column("item_code", __("Item Code"), "Data", 3),
			erpnext.item_close.column("item_name", __("Item Name"), "Data", 2),
			erpnext.item_close.column("qty", __("Qty")),
			erpnext.item_close.column("ordered_qty", __("Ordered Qty")),
			erpnext.item_close.column("pending_qty", __("Pending Qty")),
			erpnext.item_close.column("stock_uom", __("Stock UOM"), "Data"),
		],
	};
}

function update_blanket_order_status(frm, status) {
	frappe.call({
		method: "erpnext.manufacturing.doctype.blanket_order.blanket_order.update_status",
		args: { status: status, name: frm.doc.name },
		freeze: true,
		callback: () => frm.reload_doc(),
	});
}

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

function calculate_stock_qty(cdt, cdn) {
	const row = locals[cdt][cdn];
	const conversion_factor = flt(row.conversion_factor) || 1;
	return frappe.model
		.set_value(cdt, cdn, "stock_qty", flt(row.qty) * conversion_factor)
		.then(() => calculate_stock_uom_rate(cdt, cdn));
}

function calculate_stock_uom_rate(cdt, cdn) {
	const row = locals[cdt][cdn];
	const conversion_factor = flt(row.conversion_factor) || 1;
	const stock_uom_rate = row.rate ? flt(row.rate) / conversion_factor : 0;
	if (flt(row.stock_uom_rate) === flt(stock_uom_rate)) {
		return;
	}
	return frappe.model.set_value(cdt, cdn, "stock_uom_rate", stock_uom_rate);
}
