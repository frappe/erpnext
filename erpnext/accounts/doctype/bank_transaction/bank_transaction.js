// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bank Transaction", {
<<<<<<< HEAD
	setup: function (frm) {
		frm.set_query("party_type", function () {
			return {
				filters: {
					name: ["in", Object.keys(frappe.boot.party_account_types)],
				},
			};
		});

		frm.set_query("bank_account", function () {
			return {
				filters: { is_company_account: 1 },
			};
		});

=======
	onload(frm) {
>>>>>>> 7c4cf3e834 (Favicon.svg)
		frm.set_query("payment_document", "payment_entries", function () {
			const payment_doctypes = frm.events.get_payment_doctypes(frm);
			return {
				filters: {
					name: ["in", payment_doctypes],
				},
			};
		});
<<<<<<< HEAD

		frm.set_query("payment_entry", "payment_entries", function () {
			return {
				filters: {
					docstatus: ["!=", 2],
				},
			};
		});
	},

=======
	},
>>>>>>> 7c4cf3e834 (Favicon.svg)
	refresh(frm) {
		if (!frm.is_dirty() && frm.doc.payment_entries.length > 0) {
			frm.add_custom_button(__("Unreconcile Transaction"), () => {
				frm.call("remove_payment_entries").then(() => frm.refresh());
			});
		}
	},
<<<<<<< HEAD

=======
>>>>>>> 7c4cf3e834 (Favicon.svg)
	bank_account: function (frm) {
		set_bank_statement_filter(frm);
	},

<<<<<<< HEAD
=======
	setup: function (frm) {
		frm.set_query("party_type", function () {
			return {
				filters: {
					name: ["in", Object.keys(frappe.boot.party_account_types)],
				},
			};
		});
	},

>>>>>>> 7c4cf3e834 (Favicon.svg)
	get_payment_doctypes: function () {
		// get payment doctypes from all the apps
		return ["Payment Entry", "Journal Entry", "Sales Invoice", "Purchase Invoice", "Bank Transaction"];
	},
});

<<<<<<< HEAD
=======
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

>>>>>>> 7c4cf3e834 (Favicon.svg)
function set_bank_statement_filter(frm) {
	frm.set_query("bank_statement", function () {
		return {
			filters: {
				bank_account: frm.doc.bank_account,
			},
		};
	});
}
