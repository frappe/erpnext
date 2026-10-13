// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Equity Accounting Settings", {
	setup(frm) {
		[
			"cash_or_bank_account",
			"share_capital_account",
			"securities_premium_account",
			"treasury_shares_account",
			"equity_adjustment_account",
		].forEach((fieldname) => {
			frm.set_query(fieldname, () => ({
				filters: {
					company: frm.doc.company,
					is_group: 0,
					disabled: 0,
					root_type: [
						"in",
						fieldname === "cash_or_bank_account"
							? ["Asset", "Liability"]
							: ["Equity", "Liability"],
					],
					account_type: ["not in", ["Receivable", "Payable"]],
				},
			}));
		});
	},
});
