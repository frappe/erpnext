// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Warehouse", {
	setup: function (frm) {
		frm.set_query("default_in_transit_warehouse", function (doc) {
			return {
				filters: {
					warehouse_type: "Transit",
					is_group: 0,
					company: doc.company,
				},
			};
		});

		frm.set_query("parent_warehouse", function (doc) {
			return {
				filters: {
					is_group: 1,
					company: doc.company,
				},
			};
		});

		frm.set_query("account", function (doc) {
			return {
				filters: {
					is_group: 0,
					account_type: "Stock",
					company: doc.company,
				},
			};
		});
	},

	refresh: function (frm) {
		frm.toggle_display("warehouse_name", frm.doc.__islocal);
		frm.toggle_display(["address_html", "contact_html"], !frm.doc.__islocal);

		if (!frm.is_new()) {
			frappe.contacts.render_address_and_contact(frm);

			let enable_toggle = frm.doc.disabled ? "Enable" : "Disable";
			frm.add_custom_button(__(enable_toggle), () => {
				frm.set_value("disabled", 1 - frm.doc.disabled);
				frm.save();
			});

			frm.add_custom_button(__("Stock Balance"), function () {
				frappe.set_route("query-report", "Stock Balance", {
					warehouse: frm.doc.name,
					company: frm.doc.company,
				});
			});

			frm.add_custom_button(
				frm.doc.is_group
					? __("Convert to Ledger", null, "Warehouse")
					: __("Convert to Group", null, "Warehouse"),
				function () {
					convert_to_group_or_ledger(frm);
				}
			);
		} else {
			frappe.contacts.clear_address_and_contact(frm);
		}

		if (!frm.doc.is_group && frm.doc.__onload && frm.doc.__onload.account) {
			frm.add_custom_button(__("General Ledger", null, "Warehouse"), function () {
				frappe.route_options = {
					account: frm.doc.__onload.account,
					company: frm.doc.company,
				};
				frappe.set_route("query-report", "General Ledger");
			});
		}

		frm.toggle_enable(["is_group", "company"], false);
	},
});

function convert_to_group_or_ledger(frm) {
	frappe.call({
		method: "erpnext.stock.doctype.warehouse.warehouse.convert_to_group_or_ledger",
		args: {
			docname: frm.doc.name,
			is_group: frm.doc.is_group,
		},
		callback: function () {
			frm.refresh();
		},
	});
}
