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
	},

	setup: function (frm) {
		frm.custom_make_buttons = {
			"Purchase Order": "Purchase Order",
			"Sales Order": "Sales Order",
			Quotation: "Quotation",
		};

		frm.add_fetch("customer", "customer_name", "customer_name");
		frm.add_fetch("supplier", "supplier_name", "supplier_name");

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
		frm.trigger("set_dynamic_link");
		frm.trigger("clear_address_and_contact");
	},

	company: function (frm) {
		frm.trigger("set_party_address_details");
	},

	customer: function (frm) {
		frm.trigger("set_dynamic_link");
		frm.trigger("set_party_address_details");
	},

	supplier: function (frm) {
		frm.trigger("set_dynamic_link");
		frm.trigger("set_party_address_details");
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
		const party =
			frm.doc.blanket_order_type === "Selling" ? frm.doc.customer : frm.doc.supplier;
		if (!party || !frm.doc.company) {
			return;
		}

		const party_type = frm.doc.blanket_order_type === "Selling" ? "Customer" : "Supplier";
		const reference_doctype =
			frm.doc.blanket_order_type === "Selling" ? "Sales Order" : "Purchase Order";

		frappe.call({
			method: "erpnext.accounts.party.get_party_details",
			args: {
				party,
				party_type,
				company: frm.doc.company,
				doctype: reference_doctype,
				fetch_payment_terms_template: 0,
			},
			callback: function (r) {
				if (!r.message) {
					return;
				}

				const update = {};
				if (frm.doc.blanket_order_type === "Selling") {
					const selling_map = {
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
					};
					Object.assign(update, selling_map);
				} else {
					const purchasing_map = {
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
					Object.assign(update, purchasing_map);
				}

				frm.set_value(update);
			},
		});
	},
});

frappe.ui.form.on("Blanket Order Item", {
	item_code: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.item_code) {
			return;
		}

		frappe.db
			.get_value("Item", row.item_code, ["stock_uom", "sales_uom", "purchase_uom"])
			.then((r) => {
				if (!r.message) {
					return;
				}

				const default_uom =
					frm.doc.blanket_order_type === "Selling"
						? r.message.sales_uom || r.message.stock_uom
						: r.message.purchase_uom || r.message.stock_uom;

				frappe.model.set_value(cdt, cdn, "stock_uom", r.message.stock_uom);
				frappe.model.set_value(cdt, cdn, "uom", default_uom);
			});
	},

	uom: function (frm, cdt, cdn) {
		erpnext.manufacturing.doctype.blanket_order.blanket_order.set_conversion_factor(
			frm,
			cdt,
			cdn
		);
	},

	qty: function (frm, cdt, cdn) {
		erpnext.manufacturing.doctype.blanket_order.blanket_order.calculate_stock_qty(frm, cdt, cdn);
	},

	conversion_factor: function (frm, cdt, cdn) {
		erpnext.manufacturing.doctype.blanket_order.blanket_order.calculate_stock_qty(frm, cdt, cdn);
	},

	rate: function (frm, cdt, cdn) {
		erpnext.manufacturing.doctype.blanket_order.blanket_order.calculate_stock_uom_rate(
			frm,
			cdt,
			cdn
		);
	},
});

erpnext.manufacturing = erpnext.manufacturing || {};
erpnext.manufacturing.doctype = erpnext.manufacturing.doctype || {};
erpnext.manufacturing.doctype.blanket_order = erpnext.manufacturing.doctype.blanket_order || {};
erpnext.manufacturing.doctype.blanket_order.blanket_order =
	erpnext.manufacturing.doctype.blanket_order.blanket_order || {};

erpnext.manufacturing.doctype.blanket_order.blanket_order.set_conversion_factor = function (
	frm,
	cdt,
	cdn
) {
	const row = locals[cdt][cdn];
	if (!row.item_code || !row.uom) {
		return;
	}

	if (row.uom === row.stock_uom) {
		frappe.model.set_value(cdt, cdn, "conversion_factor", 1);
		erpnext.manufacturing.doctype.blanket_order.blanket_order.calculate_stock_qty(frm, cdt, cdn);
		return;
	}

	frappe.call({
		method: "erpnext.stock.get_item_details.get_conversion_factor",
		args: {
			item_code: row.item_code,
			uom: row.uom,
		},
		callback: function (r) {
			if (!r.exc) {
				frappe.model.set_value(cdt, cdn, "conversion_factor", r.message.conversion_factor);
			}
		},
	});
};

erpnext.manufacturing.doctype.blanket_order.blanket_order.calculate_stock_qty = function (
	frm,
	cdt,
	cdn
) {
	const row = locals[cdt][cdn];
	if (!row.qty && !row.conversion_factor) {
		return;
	}

	const conversion_factor = flt(row.conversion_factor) || 1;
	frappe.model.set_value(cdt, cdn, "stock_qty", flt(row.qty) * conversion_factor);
	erpnext.manufacturing.doctype.blanket_order.blanket_order.calculate_stock_uom_rate(
		frm,
		cdt,
		cdn
	);
};

erpnext.manufacturing.doctype.blanket_order.blanket_order.calculate_stock_uom_rate = function (
	frm,
	cdt,
	cdn
) {
	const row = locals[cdt][cdn];
	const conversion_factor = flt(row.conversion_factor) || 1;
	if (row.rate) {
		frappe.model.set_value(cdt, cdn, "stock_uom_rate", flt(row.rate) / conversion_factor);
	}
};
