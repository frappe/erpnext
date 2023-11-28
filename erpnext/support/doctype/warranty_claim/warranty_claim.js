// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.support");

frappe.ui.form.on("Warranty Claim", {
	setup: (frm) => {
		frm.set_query("contact_person", erpnext.queries.contact_query);
		frm.set_query("customer_address", erpnext.queries.address_query);
		frm.set_query("customer", erpnext.queries.customer);

		frm.set_query("serial_no", () => {
			let filters = {
				company: frm.doc.company,
			};

			if (frm.doc.item_code) {
				filters["item_code"] = frm.doc.item_code;
			}

			return { filters: filters };
		});

		frm.set_query("item_code", () => {
			return {
				filters: {
					disabled: 0,
				},
			};
		});
	},

	onload: (frm) => {
		if (!frm.doc.status) {
			frm.set_value("status", "Open");
		}
	},

	customer: (frm) => {
		erpnext.utils.get_party_details(frm);
	},

	customer_address: (frm) => {
		erpnext.utils.get_address_display(frm);
	},

	contact_person: (frm) => {
		erpnext.utils.get_contact_details(frm);
	},
});

erpnext.support.WarrantyClaim = class WarrantyClaim extends (
	frappe.ui.form.Controller
) {
	refresh() {
		frappe.dynamic_link = {
			doc: this.frm.doc,
			fieldname: "customer",
			doctype: "Customer",
		};

		if (
			!cur_frm.doc.__islocal &&
			(cur_frm.doc.status == "Open" ||
				cur_frm.doc.status == "Work In Progress")
		) {
			cur_frm.add_custom_button(
				__("Maintenance Visit"),
				this.make_maintenance_visit
			);
		}
	}

	make_maintenance_visit() {
		frappe.model.open_mapped_doc({
			method: "erpnext.support.doctype.warranty_claim.warranty_claim.make_maintenance_visit",
			frm: cur_frm,
		});
	}
};

extend_cscript(
	cur_frm.cscript,
	new erpnext.support.WarrantyClaim({ frm: cur_frm })
);
