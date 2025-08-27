// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Blanket Order", {
	onload: function (frm) {
		frm.trigger("set_tc_name_filter");
	},

	setup: function (frm) {
		frm.custom_make_buttons = {
			"Purchase Order": "Purchase Order",
			"Sales Order": "Sales Order",
			Quotation: "Quotation",
		};
		frm.add_fetch("customer", "customer_name", "customer_name");
		frm.add_fetch("supplier", "supplier_name", "supplier_name");
	},

	refresh: function (frm) {
		erpnext.hide_company(frm);
		if (frm.doc.customer && frm.doc.docstatus === 1 && frm.doc.to_date > frappe.datetime.get_today()) {
			frm.add_custom_button(
				__("Sales Order"),
				function () {
					frappe.model.open_mapped_doc({
						method: "erpnext.manufacturing.doctype.blanket_order.blanket_order.make_order",
						frm: frm,
						args: { doctype: "Sales Order" },
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
						args: { doctype: "Quotation" },
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
						args: { doctype: "Purchase Order" },
					});
				},
				__("Create")
			);
		}
		frm.trigger("set_dynamic_grid_labels");
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
	},

	company: function (frm) {
		set_party_currency(frm);
	},

	supplier: function (frm) {
		set_party_currency(frm);
	},

	customer: function (frm) {
		set_party_currency(frm);
	},

	currency: function (frm) {
		let order_date = frm.doc.from_date || frappe.datetime.get_today();
		let company_currency = erpnext.get_currency(frm.doc.company);

		frm.trigger("set_dynamic_grid_labels");

		if (frm.doc.currency !== company_currency) {
			frappe.call({
				method: "erpnext.setup.utils.get_exchange_rate",
				args: {
					transaction_date: order_date,
					from_currency: frm.doc.currency,
					to_currency: company_currency,
				},
				freeze: true,
				freeze_message: __("Fetching exchange rates ..."),
				callback: function (r) {
					if (r.message) {
						frm.set_value("conversion_rate", r.message);
						frm.set_df_property(
							"conversion_rate",
							"description",
							"1 " + frm.doc.currency + " = [?] " + company_currency
						);
						frm.trigger("calculate_base_rate");
					}
				},
			});
		} else {
			frm.set_value("conversion_rate", 1.0);
			frm.trigger("calculate_base_rate");
		}
	},

	from_date: function (frm) {
		frm.trigger("currency");
	},

	calculate_base_rate: function (frm) {
		frm.doc.items.forEach(function (row) {
			frappe.model.set_value(
				row.doctype,
				row.name,
				"base_rate",
				flt(row.rate * frm.doc.conversion_rate)
			);
		});
		frm.refresh_field("items");
	},

	set_dynamic_grid_labels: function (frm) {
		let company_currency = get_company_currency(frm.doc.company);
		let party_currency = frm.doc.currency;

		frm.set_currency_labels(["rate"], party_currency, "items");
		frm.set_currency_labels(["base_rate"], company_currency, "items");
		frm.refresh_fields();
	},
});

frappe.ui.form.on("Blanket Order Item", {
	calculate: function (frm, cdt, cdn) {
		let row = frappe.get_doc(cdt, cdn);
		frappe.model.set_value(cdt, cdn, "base_rate", flt(frm.doc.conversion_rate) * flt(row.rate));
	},
	rate: function (frm, cdt, cdn) {
		frm.trigger("calculate", cdt, cdn);
	},
	qty: function (frm, cdt, cdn) {
		frm.trigger("calculate", cdt, cdn);
	},
});

const get_company_currency = function (company) {
	return erpnext.get_currency(company);
};

const set_party_currency = function (frm) {
	var party_type = frm.doc.blanket_order_type === "Purchasing" ? "Supplier" : "Customer";
	var party_name = frm.doc[party_type.toLowerCase()];

	if (party_name) {
		frappe.call({
			method: "frappe.client.get_value",
			args: {
				doctype: party_type,
				filters: { name: party_name },
				fieldname: "default_currency",
			},
			callback: function (r) {
				if (r.message && r.message.default_currency) {
					if (frm.doc.currency !== r.message.default_currency) {
						frm.set_value("currency", r.message.default_currency);
					} else {
						frm.trigger("currency");
					}
				} else {
					frm.set_value("currency", get_company_currency(frm.doc.company));
				}
			},
		});
	} else {
		frm.set_value("currency", get_company_currency(frm.doc.company));
	}
};
