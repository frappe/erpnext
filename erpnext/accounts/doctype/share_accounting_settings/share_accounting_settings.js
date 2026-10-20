// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

const ROOT_TYPES = {
	clearing_account: ["Asset", "Liability"],
	default_bank_account: ["Asset", "Liability"],
	share_capital_account: ["Equity", "Liability"],
	securities_premium_account: ["Equity", "Liability"],
	treasury_shares_account: ["Equity", "Liability"],
	treasury_adjustment_account: ["Equity", "Liability"],
};

frappe.ui.form.on("Share Accounting Settings", {
	setup(frm) {
		Object.entries(ROOT_TYPES).forEach(([fieldname, root_types]) => {
			frm.set_query(fieldname, () => ({
				filters: {
					company: frm.doc.company,
					is_group: 0,
					disabled: 0,
					root_type: ["in", root_types],
					account_type: ["not in", ["Receivable", "Payable"]],
				},
			}));
		});
	},
});
