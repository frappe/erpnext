// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bank Transaction", {
	onload(frm) {
		frm.set_query("payment_document", "payment_entries", function () {
			const payment_doctypes = frm.events.get_payment_doctypes(frm);
			return {
				filters: {
					name: ["in", payment_doctypes],
				},
			};
		});
	},
	refresh(frm) {
		if (!frm.is_dirty() && frm.doc.payment_entries.length > 0) {
			frm.add_custom_button(__("Unreconcile Transaction"), () => {
				frm.call("remove_payment_entries").then(() => frm.refresh());
			});
		}
	},
	bank_account: function (frm) {
		set_bank_statement_filter(frm);
	},

	setup: function (frm) {
		frm.set_query("party_type", function () {
			return {
				filters: {
					name: ["in", Object.keys(frappe.boot.party_account_types)],
				},
			};
		});
	},

	get_payment_doctypes: function () {
		// get payment doctypes from all the apps
		return ["Payment Entry", "Journal Entry", "Sales Invoice", "Purchase Invoice", "Bank Transaction"];
	},
});

frappe.ui.form.on("Bank Transaction Payments", {
	payment_entries_remove: function (frm, cdt, cdn) {
		update_clearance_date(frm, cdt, cdn);
	},
});

const update_clearance_date = (frm, cdt, cdn) => {
	if (frm.doc.docstatus === 1) {
		frappe
			.xcall("erpnext.accounts.doctype.bank_transaction.bank_transaction.unclear_reference_payment", {
				doctype: cdt,
				docname: cdn,
				bt_name: frm.doc.name,
			})
			.then((e) => {
				if (e == "success") {
					frappe.show_alert({
						message: __("Document {0} successfully uncleared", [e]),
						indicator: "green",
					});
				}
			});
	}
};

function set_bank_statement_filter(frm) {
	frm.set_query("bank_statement", function () {
		return {
			filters: {
				bank_account: frm.doc.bank_account,
			},
		};
	});
}
