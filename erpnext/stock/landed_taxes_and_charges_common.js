let document_list = ['Landed Cost Voucher', 'Stock Entry'];

document_list.forEach((doctype) => {
	frappe.ui.form.on(doctype, {
		refresh: function(frm) {
			let tax_field = frm.doc.doctype == 'Landed Cost Voucher' ? 'taxes' : 'additional_costs';
			frm.set_query("expense_account", tax_field, function() {
				return {
					filters: {
						"account_type": ['in', ["Tax", "Chargeable", "Income Account", "Expenses Included In Valuation", "Expenses Included In Asset Valuation"]],
						"company": frm.doc.company
					}
				};
			});
		},

		set_account_currency: function(frm, cdt, cdn) {
			let row = locals[cdt][cdn];
			if (row.expense_account) {
				frappe.db.get_value('Account', row.expense_account, 'account_currency', function(value) {
					frappe.model.set_value(cdt, cdn, "account_currency", value.account_currency);
					frm.events.set_exchange_rate(frm, cdt, cdn);
				});
			}
		},

		set_exchange_rate: function(frm, cdt, cdn) {
			let row = locals[cdt][cdn];
			let company_currency = frappe.get_doc(":Company", frm.doc.company).default_currency;

			if (row.account_currency == company_currency) {
				row.exchange_rate = 1;
				frm.set_df_property('taxes', 'hidden', 1, row.name, 'exchange_rate');
			} else if (!row.exchange_rate || row.exchange_rate == 1) {
				frm.set_df_property('taxes', 'hidden', 0, row.name, 'exchange_rate');
				frappe.call({
					method: "erpnext.accounts.doctype.journal_entry.journal_entry.get_exchange_rate",
					args: {
						posting_date: frm.doc.posting_date,
						account: row.expense_account,
						account_currency: row.account_currency,
						company: frm.doc.company
					},
					callback: function(r) {
						if (r.message) {
							frappe.model.set_value(cdt, cdn, "exchange_rate", r.message);
						}
					}
				});
			}

			frm.refresh_field('taxes');
		},

		set_base_amount: function(frm, cdt, cdn) {
			let row = locals[cdt][cdn];
			frappe.model.set_value(cdt, cdn, "base_amount",
				flt(flt(row.amount)*row.exchange_rate, precision("base_amount", row)));
		}
	});
});
