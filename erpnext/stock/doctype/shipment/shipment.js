// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Shipment", {
	address_query: function (frm, link_doctype, link_name, is_your_company_address) {
		return {
			query: "frappe.contacts.doctype.address.address.address_query",
			filters: {
				link_doctype: link_doctype,
				link_name: link_name,
				is_your_company_address: is_your_company_address,
			},
		};
	},
	contact_query: function (frm, link_doctype, link_name) {
		return {
			query: "frappe.contacts.doctype.contact.contact.contact_query",
			filters: {
				link_doctype: link_doctype,
				link_name: link_name,
			},
		};
	},
	onload: function (frm) {
		frm.set_query("delivery_address_name", () => {
			let delivery_to = `delivery_${frappe.model.scrub(frm.doc.delivery_to_type)}`;
			return frm.events.address_query(
				frm,
				frm.doc.delivery_to_type,
				frm.doc[delivery_to],
				frm.doc.delivery_to_type === "Company" ? 1 : 0
			);
		});
		frm.set_query("pickup_address_name", () => {
			let pickup_from = `pickup_${frappe.model.scrub(frm.doc.pickup_from_type)}`;
			return frm.events.address_query(
				frm,
				frm.doc.pickup_from_type,
				frm.doc[pickup_from],
				frm.doc.pickup_from_type === "Company" ? 1 : 0
			);
		});
		frm.set_query("delivery_contact_name", () => {
			let delivery_to = `delivery_${frappe.model.scrub(frm.doc.delivery_to_type)}`;
			return frm.events.contact_query(frm, frm.doc.delivery_to_type, frm.doc[delivery_to]);
		});
		frm.set_query("pickup_contact_name", () => {
			let pickup_from = `pickup_${frappe.model.scrub(frm.doc.pickup_from_type)}`;
			return frm.events.contact_query(frm, frm.doc.pickup_from_type, frm.doc[pickup_from]);
		});
		frm.set_query("delivery_note", "shipment_delivery_note", function () {
			let customer = "";
			if (frm.doc.delivery_to_type == "Customer") {
				customer = frm.doc.delivery_customer;
			}
			if (frm.doc.delivery_to_type == "Company") {
				customer = frm.doc.delivery_company;
			}
			if (customer) {
				return {
					filters: {
						customer: customer,
						docstatus: 1,
						status: ["not in", ["Cancelled"]],
					},
				};
			}
		});
	},
	refresh: function () {
		$("div[data-fieldname=pickup_address] > div > .clearfix").hide();
		$("div[data-fieldname=pickup_contact] > div > .clearfix").hide();
		$("div[data-fieldname=delivery_address] > div > .clearfix").hide();
		$("div[data-fieldname=delivery_contact] > div > .clearfix").hide();
	},
	before_save: function (frm) {
		let delivery_to = `delivery_${frappe.model.scrub(frm.doc.delivery_to_type)}`;
		frm.set_value("delivery_to", frm.doc[delivery_to]);
		let pickup_from = `pickup_${frappe.model.scrub(frm.doc.pickup_from_type)}`;
		frm.set_value("pickup", frm.doc[pickup_from]);
	},
	set_pickup_company_address: function (frm) {
		frappe.db.get_value(
			"Address",
			{
				address_title: frm.doc.pickup_company,
				is_your_company_address: 1,
			},
			"name",
			(r) => {
				frm.set_value("pickup_address_name", r.name);
			}
		);
	},
	set_delivery_company_address: function (frm) {
		frappe.db.get_value(
			"Address",
			{
				address_title: frm.doc.delivery_company,
				is_your_company_address: 1,
			},
			"name",
			(r) => {
				frm.set_value("delivery_address_name", r.name);
			}
		);
	},
	pickup_from_type: function (frm) {
		if (frm.doc.pickup_from_type == "Company") {
			frm.set_value("pickup_company", frappe.defaults.get_default("company"));
			frm.set_value("pickup_customer", "");
			frm.set_value("pickup_supplier", "");
		} else {
			frm.trigger("clear_pickup_fields");
		}
		if (frm.doc.pickup_from_type == "Customer") {
			frm.set_value("pickup_company", "");
			frm.set_value("pickup_supplier", "");
		}
		if (frm.doc.pickup_from_type == "Supplier") {
			frm.set_value("pickup_customer", "");
			frm.set_value("pickup_company", "");
		}
	},
	delivery_to_type: function (frm) {
		if (frm.doc.delivery_to_type == "Company") {
			frm.set_value("delivery_company", frappe.defaults.get_default("company"));
			frm.set_value("delivery_customer", "");
			frm.set_value("delivery_supplier", "");
		} else {
			frm.trigger("clear_delivery_fields");
		}
		if (frm.doc.delivery_to_type == "Customer") {
			frm.set_value("delivery_company", "");
			frm.set_value("delivery_supplier", "");
		}
		if (frm.doc.delivery_to_type == "Supplier") {
			frm.set_value("delivery_customer", "");
			frm.set_value("delivery_company", "");
			frm.toggle_display("shipment_delivery_note", false);
		} else {
			frm.toggle_display("shipment_delivery_note", true);
		}
	},
	delivery_address_name: function (frm) {
		if (frm.doc.delivery_to_type == "Company") {
			erpnext.utils.get_address_display(frm, "delivery_address_name", "delivery_address", true);
		} else {
			erpnext.utils.get_address_display(frm, "delivery_address_name", "delivery_address", false);
		}
	},
	pickup_address_name: function (frm) {
		if (frm.doc.pickup_from_type == "Company") {
			erpnext.utils.get_address_display(frm, "pickup_address_name", "pickup_address", true);
		} else {
			erpnext.utils.get_address_display(frm, "pickup_address_name", "pickup_address", false);
		}
	},
	get_contact_display: function (frm, contact_name, contact_type) {
		frappe.call({
			method: "frappe.contacts.doctype.contact.contact.get_contact_details",
			args: { contact: contact_name },
			callback: function (r) {
				if (r.message) {
					if (!(r.message.contact_email || r.message.contact_phone || r.message.contact_mobile)) {
						if (contact_type == "Delivery") {
							frm.set_value("delivery_contact_name", "");
							frm.set_value("delivery_contact", "");
						} else {
							frm.set_value("pickup_contact_name", "");
							frm.set_value("pickup_contact", "");
						}
						frappe.throw(
							__("Email or Phone/Mobile of the Contact are mandatory to continue.") +
								"</br>" +
								__("Please set Email/Phone for the contact") +
								` <a href='/app/contact/${contact_name}'>${contact_name}</a>`
						);
					}
					let contact_display = r.message.contact_display;
					if (r.message.contact_email) {
						contact_display += "<br>" + r.message.contact_email;
					}
					if (r.message.contact_phone) {
						contact_display += "<br>" + r.message.contact_phone;
					}
					if (r.message.contact_mobile && !r.message.contact_phone) {
						contact_display += "<br>" + r.message.contact_mobile;
					}
					if (contact_type == "Delivery") {
						frm.set_value("delivery_contact", contact_display);
						if (r.message.contact_email) {
							frm.set_value("delivery_contact_email", r.message.contact_email);
						}
					} else {
						frm.set_value("pickup_contact", contact_display);
						if (r.message.contact_email) {
							frm.set_value("pickup_contact_email", r.message.contact_email);
						}
					}
				}
			},
		});
	},
	delivery_contact_name: function (frm) {
		if (frm.doc.delivery_contact_name) {
			frm.events.get_contact_display(frm, frm.doc.delivery_contact_name, "Delivery");
		}
	},
	pickup_contact_name: function (frm) {
		if (frm.doc.pickup_contact_name) {
			frm.events.get_contact_display(frm, frm.doc.pickup_contact_name, "Pickup");
		}
	},
	pickup_contact_person: function (frm) {
		if (frm.doc.pickup_contact_person) {
			frappe.call({
				method: "erpnext.stock.doctype.shipment.shipment.get_company_contact",
				args: { user: frm.doc.pickup_contact_person },
				callback: function ({ message }) {
					const r = message;
					let contact_display = `${r.first_name} ${r.last_name}`;
					if (r.email) {
						contact_display += `<br>${r.email}`;
						frm.set_value("pickup_contact_email", r.email);
					}
					if (r.phone) {
						contact_display += `<br>${r.phone}`;
					}
					if (r.mobile_no && !r.phone) {
						contact_display += `<br>${r.mobile_no}`;
					}
					frm.set_value("pickup_contact", contact_display);
				},
			});
		} else {
			if (frm.doc.pickup_from_type === "Company") {
				frappe.call({
					method: "erpnext.stock.doctype.shipment.shipment.get_company_contact",
					args: { user: frappe.session.user },
					callback: function ({ message }) {
						const r = message;
						let contact_display = `${r.first_name} ${r.last_name}`;
						if (r.email) {
							contact_display += `<br>${r.email}`;
							frm.set_value("pickup_contact_email", r.email);
						}
						if (r.phone) {
							contact_display += `<br>${r.phone}`;
						}
						if (r.mobile_no && !r.phone) {
							contact_display += `<br>${r.mobile_no}`;
						}
						frm.set_value("pickup_contact", contact_display);
					},
				});
			}
		}
	},
	set_company_contact: function (frm, delivery_type) {
		frappe.db.get_value(
			"User",
			{ name: frappe.session.user },
			["full_name", "last_name", "email", "phone", "mobile_no"],
			(r) => {
				if (!(r.last_name && r.email && (r.phone || r.mobile_no))) {
					if (delivery_type == "Delivery") {
						frm.set_value("delivery_company", "");
						frm.set_value("delivery_contact", "");
					} else {
						frm.set_value("pickup_company", "");
						frm.set_value("pickup_contact", "");
					}
					frappe.throw(
						__("Last Name, Email or Phone/Mobile of the user are mandatory to continue.") +
							"</br>" +
							__("Please first set Last Name, Email and Phone for the user") +
							` <a href="/app/user/${frappe.session.user}">${frappe.session.user}</a>`
					);
				}
				let contact_display = r.full_name;
				if (r.email) {
					contact_display += "<br>" + r.email;
				}
				if (r.phone) {
					contact_display += "<br>" + r.phone;
				}
				if (r.mobile_no && !r.phone) {
					contact_display += "<br>" + r.mobile_no;
				}
				if (delivery_type == "Delivery") {
					frm.set_value("delivery_contact", contact_display);
					if (r.email) {
						frm.set_value("delivery_contact_email", r.email);
					}
				} else {
					frm.set_value("pickup_contact", contact_display);
					if (r.email) {
						frm.set_value("pickup_contact_email", r.email);
					}
				}
			}
		);
		frm.set_value("pickup_contact_person", frappe.session.user);
	},
	pickup_company: function (frm) {
		if (frm.doc.pickup_from_type == "Company" && frm.doc.pickup_company) {
			frm.trigger("set_pickup_company_address");
			frm.events.set_company_contact(frm, "Pickup");
		}
	},
	delivery_company: function (frm) {
		if (frm.doc.delivery_to_type == "Company" && frm.doc.delivery_company) {
			frm.trigger("set_delivery_company_address");
			frm.events.set_company_contact(frm, "Delivery");
		}
	},
	delivery_customer: function (frm) {
		frm.trigger("clear_delivery_fields");
		if (frm.doc.delivery_customer) {
			frm.events.set_address_name(frm, "Customer", frm.doc.delivery_customer, "Delivery");
			frm.events.set_contact_name(frm, "Customer", frm.doc.delivery_customer, "Delivery");
		}
	},
	delivery_supplier: function (frm) {
		frm.trigger("clear_delivery_fields");
		if (frm.doc.delivery_supplier) {
			frm.events.set_address_name(frm, "Supplier", frm.doc.delivery_supplier, "Delivery");
			frm.events.set_contact_name(frm, "Supplier", frm.doc.delivery_supplier, "Delivery");
		}
	},
	pickup_customer: function (frm) {
		if (frm.doc.pickup_customer) {
			frm.events.set_address_name(frm, "Customer", frm.doc.pickup_customer, "Pickup");
			frm.events.set_contact_name(frm, "Customer", frm.doc.pickup_customer, "Pickup");
		}
	},
	pickup_supplier: function (frm) {
		if (frm.doc.pickup_supplier) {
			frm.events.set_address_name(frm, "Supplier", frm.doc.pickup_supplier, "Pickup");
			frm.events.set_contact_name(frm, "Supplier", frm.doc.pickup_supplier, "Pickup");
		}
	},
	set_address_name: function (frm, ref_doctype, ref_docname, delivery_type) {
		frappe.call({
			method: "erpnext.stock.doctype.shipment.shipment.get_address_name",
			args: {
				ref_doctype: ref_doctype,
				docname: ref_docname,
			},
			callback: function (r) {
				if (r.message) {
					if (delivery_type == "Delivery") {
						frm.set_value("delivery_address_name", r.message);
					} else {
						frm.set_value("pickup_address_name", r.message);
					}
				}
			},
		});
	},
	set_contact_name: function (frm, ref_doctype, ref_docname, delivery_type) {
		frappe.call({
			method: "erpnext.stock.doctype.shipment.shipment.get_contact_name",
			args: {
				ref_doctype: ref_doctype,
				docname: ref_docname,
			},
			callback: function (r) {
				if (r.message) {
					if (delivery_type == "Delivery") {
						frm.set_value("delivery_contact_name", r.message);
					} else {
						frm.set_value("pickup_contact_name", r.message);
					}
				}
			},
		});
	},
	add_template: function (frm) {
		if (frm.doc.parcel_template) {
			frappe.model.with_doc("Shipment Parcel Template", frm.doc.parcel_template, () => {
				let parcel_template = frappe.model.get_doc(
					"Shipment Parcel Template",
					frm.doc.parcel_template
				);
				let row = frappe.model.add_child(frm.doc, "Shipment Parcel", "shipment_parcel");
				row.length = parcel_template.length;
				row.width = parcel_template.width;
				row.height = parcel_template.height;
				row.weight = parcel_template.weight;
				frm.refresh_fields("shipment_parcel");
			});
		}
	},
	pickup_date: function (frm) {
		if (frm.doc.pickup_date < frappe.datetime.get_today()) {
			frappe.throw(__("Pickup Date cannot be before this day"));
		}
	},
	clear_pickup_fields: function (frm) {
		let fields = [
			"pickup_address_name",
			"pickup_contact_name",
			"pickup_address",
			"pickup_contact",
			"pickup_contact_email",
			"pickup_contact_person",
		];
		for (let field of fields) {
			frm.set_value(field, "");
		}
	},
	clear_delivery_fields: function (frm) {
		let fields = [
			"delivery_address_name",
			"delivery_contact_name",
			"delivery_address",
			"delivery_contact",
			"delivery_contact_email",
		];
		for (let field of fields) {
			frm.set_value(field, "");
		}
	},
	remove_email_row: function (frm, table, fieldname) {
		$.each(frm.doc[table] || [], function (i, detail) {
			if (detail.email === fieldname) {
				cur_frm.get_field(table).grid.grid_rows[i].remove();
			}
		});
	},
});

frappe.ui.form.on("Shipment Delivery Note", {
	delivery_note: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.delivery_note) {
			let row_index = row.idx - 1;
			if (validate_duplicate(frm, "shipment_delivery_note", row.delivery_note, row_index)) {
				frappe.throw(
					__("You have entered a duplicate Delivery Note on Row") +
						` ${row.idx}. ` +
						__("Please rectify and try again.")
				);
			}
		}
	},
	grand_total: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.grand_total) {
			var value_of_goods = parseFloat(frm.doc.value_of_goods) + parseFloat(row.grand_total);
			frm.set_value("value_of_goods", Math.round(value_of_goods));
			frm.refresh_fields("value_of_goods");
		}
	},
});

var validate_duplicate = function (frm, table, fieldname, index) {
	return table === "shipment_delivery_note"
		? frm.doc[table].some((detail, i) => detail.delivery_note === fieldname && !(index === i))
		: frm.doc[table].some((detail, i) => detail.email === fieldname && !(index === i));
};
