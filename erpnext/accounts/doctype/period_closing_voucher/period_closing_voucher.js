// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Period Closing Voucher", {
	onload: function (frm) {
		if (!frm.doc.transaction_date) frm.doc.transaction_date = frappe.datetime.obj_to_str(new Date());

		frm.ignore_doctypes_on_cancel_all = ["Process Period Closing Voucher"];
	},

	setup: function (frm) {
		frm.set_query("closing_account_head", function () {
			return {
				filters: [
					["Account", "company", "=", frm.doc.company],
					["Account", "is_group", "=", 0],
					["Account", "freeze_account", "=", "No"],
					["Account", "root_type", "in", ["Liability", "Equity"]],
				],
			};
		});
	},

	fiscal_year: function (frm) {
		if (frm.doc.fiscal_year) {
			frappe.call({
				method: "erpnext.accounts.doctype.period_closing_voucher.period_closing_voucher.get_period_start_end_date",
				args: {
					fiscal_year: frm.doc.fiscal_year,
					company: frm.doc.company,
				},
				callback: function (r) {
					if (r.message) {
						frm.set_value("period_start_date", r.message[0]);
						frm.set_value("period_end_date", r.message[1]);
					}
				},
			});
		}
	},

	before_submit(frm) {
		frm.doc.stock_value_difference = 0;

		return frm.call("get_stock_value_difference").then(({ message }) => {
			if (!message?.within_tolerance) return;

			return new Promise((resolve) => {
				const currency = erpnext.get_currency(frm.doc.company);
				frappe.confirm(
					__(
						"The closing balance {0} of the Stock Asset accounts differs from the closing value {1} of the Stock Balance report by {2}, which is within the allowed {3}% tolerance. Submit the Period Closing Voucher with this difference?",
						[
							format_currency(message.account_balance, currency),
							format_currency(message.stock_value, currency),
							format_currency(message.difference, currency),
							message.tolerance,
						]
					),
					() => {
						frm.doc.stock_value_difference = message.difference;
						resolve();
					},
					() => {
						frappe.validated = false;
						resolve();
					}
				);
			});
		});
	},

	refresh: function (frm) {
		if (frm.doc.docstatus > 0) {
			frm.add_custom_button(__("Ledger"), function () {
				frappe.route_options = {
					voucher_no: frm.doc.name,
					from_date: frm.doc.period_start_date,
					to_date: frm.doc.period_end_date,
					company: frm.doc.company,
					categorize_by: "",
					show_cancelled_entries: frm.doc.docstatus === 2,
				};
				frappe.set_route("query-report", "General Ledger");
			});
		}
	},
});
