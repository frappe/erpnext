// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

// Set Tax amount
// Get Supplier default expense account
// Get Tax Rate from Supplier or Tax Account
// Check for duplicate bill_no in Expense Entry Detail rows for that party

frappe.provide("erpnext.accounts.expense_entry");

frappe.ui.form.on('Expense Entry', {
	setup: function(frm) {
		frm.page.toggle_sidebar();

		frm.set_query('payable_account', function() {
			if(!frm.doc.company) {
				frappe.msgprint(__("Please select Company first"));
			} else {
				return {
					filters:[
						['Account', 'company', '=', frm.doc.company],
						['Account', 'is_group', '=', 0],
						['Account', 'account_type', '=', 'Payable']
					]
				};
			}
		});

		frm.set_query('paid_from_account', function() {
			if(!frm.doc.company) {
				frappe.msgprint(__("Please select Company first"));
			} else {
				return {
					filters:[
						['Account', 'company', '=', frm.doc.company],
						['Account', 'is_group', '=', 0],
						['Account', 'account_type', 'in', ['Bank', 'Cash', 'Equity']]
					]
				};
			}
		});

		frm.set_query("expense_account", "accounts", function() {
			if(!frm.doc.company) {
				frappe.msgprint(__("Please select Company first"));
			} else {
				return {
					filters: [
						['Account', 'company', '=', frm.doc.company],
						['Account', 'is_group', '=', 0],
					]
				}
			}
		});
	},

	refresh: function (frm) {
		erpnext.hide_company();
	},

	payable_account: function (frm) {
		if (!frm.doc.payable_account) {
			var company_currency = frappe.get_doc(":Company", frm.doc.company).default_currency;
			frm.set_value("payable_account_currency", company_currency);
		}
	},

	payable_account_currency: function (frm) {
		var company_currency = frappe.get_doc(":Company", frm.doc.company).default_currency;
		var bill_dates = [];
		$.each(frm.doc.accounts || [], function (i, d) {
			if (d.bill_date && !bill_dates.includes(d.bill_date)) {
				bill_dates.push(d.bill_date || frm.doc.transaction_date);
			}
		});

		if (company_currency == frm.doc.payable_account_currency) {
			$.each(frm.doc.accounts || [], function (i, d) {
				if (d.bill_date) {
					d.exchange_rate = 1.0;
				}
			});
			erpnext.accounts.expense_entry.calcualte_totals(frm);
		} else {
			frappe.call({
				method: "erpnext.accounts.doctype.expense_entry.expense_entry.get_exchange_rates",
				args: {
					bill_dates: bill_dates,
					from_currency: frm.doc.payable_account_currency,
					to_currency: company_currency
				},
				callback: function (r) {
					$.each(frm.doc.accounts || [], function (i, d) {
						if (d.bill_date && r.message[d.bill_date]) {
							d.exchange_rate = r.message[d.bill_date];
						}
					});
					erpnext.accounts.expense_entry.calcualte_totals(frm);
				}
			});
		}
	}
});

frappe.ui.form.on('Expense Entry Detail', {
	bill_date: function (frm, cdt, cdn) {
		erpnext.accounts.expense_entry.set_exchange_rate(frm, cdt, cdn);
	},

	bill_no: function(frm, cdt, cdn) {
		erpnext.accounts.expense_entry.check_duplicate_bill_no(frm, cdt, cdn);
	},

	supplier: function (frm, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);

		if (row.supplier && !row.expense_account) {
			frappe.call({
				method: "erpnext.accounts.doctype.expense_entry.expense_entry.get_default_expense_account",
				args: {
					supplier: row.supplier
				},
				callback: function (r) {
					frappe.model.set_value(cdt, cdn, 'expense_account', r.message);
				}
			});
		}

		erpnext.accounts.expense_entry.check_duplicate_bill_no(frm, cdt, cdn);
	},

	total_amount: function (frm, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		if (row.item_tax_template) {
			erpnext.accounts.expense_entry.calculate_tax_amount(frm, cdt, cdn);
		} else {
			erpnext.accounts.expense_entry.calcualte_totals(frm);
		}
	},

	tax_amount: function (frm, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		if (!row.item_tax_template) {
			row.tax_amount = 0;
		}
		erpnext.accounts.expense_entry.calcualte_totals(frm);
	},

	item_tax_template: function (frm, cdt, cdn) {
		erpnext.accounts.expense_entry.get_tax_rate(frm, cdt, cdn);
	},

	tax_rate: function (frm, cdt, cdn) {
		erpnext.accounts.expense_entry.calculate_tax_amount(frm, cdt, cdn);
	},

	exchange_rate: function (frm, cdt, cdn) {
		var company_currency = frappe.get_doc(":Company", frm.doc.company).default_currency;
		var row = frappe.get_doc(cdt, cdn);
		if (frm.doc.payable_account_currency == company_currency) {
			row.exchange_rate = 1.0;
		}

		erpnext.accounts.expense_entry.calcualte_totals(frm);
	}
});

$.extend(erpnext.accounts.expense_entry, {
	calcualte_totals: function(frm) {
		$.each(frm.doc.accounts || [], function (i, d) {
			d.expense_amount = flt(flt(d.total_amount) - flt(d.tax_amount), precision('expense_amount', d));

			d.base_total_amount = flt(flt(d.total_amount) * flt(d.exchange_rate), precision('base_total_amount', d));
			d.base_tax_amount = flt(flt(d.tax_amount) * flt(d.exchange_rate), precision('base_tax_amount', d));
			d.base_expense_amount = flt(flt(d.base_total_amount) - flt(d.base_tax_amount), precision('base_expense_amount', d));
		});

		var total_fields = [
			['total', 'total_amount'],
			['total_tax_amount', 'tax_amount'],
			['total_expense_amount', 'expense_amount'],
		]
		$.each(total_fields, function (i, f) {
			frm.doc[f[0]] = flt(frappe.utils.sum(frm.doc.accounts.map(d => flt(d[f[1]]))), precision(f[0]));
			frm.doc["base_" + f[0]] = flt(frappe.utils.sum(frm.doc.accounts.map(d => flt(d["base_" + f[1]]))), precision("base_" + f[0]));
		});

		frm.refresh_fields();
	},

	calculate_tax_amount: function(frm, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);

		var tax_map = JSON.parse(row.tax_rate || '{}');
		var tax_amount = 0;
		$.each(tax_map, function (tax_type, tax_rate) {
			if (tax_rate) {
				tax_amount += flt(row.total_amount) - flt(row.total_amount) / (1 + flt(tax_rate) / 100);
			}
		});

		tax_amount = flt(tax_amount, precision("tax_amount", row));
		frappe.model.set_value(cdt, cdn, 'tax_amount', tax_amount);
	},

	set_exchange_rate: function(frm, cdt, cdn) {
		var company_currency = frappe.get_doc(":Company", frm.doc.company).default_currency;
		var row = frappe.get_doc(cdt, cdn);

		if (frm.doc.payable_account_currency === company_currency) {
			frappe.model.set_value(cdt, cdn, 'exchange_rate', 1);
		} else if (row.bill_date) {
			frappe.call({
				method: "erpnext.setup.utils.get_exchange_rate",
				args: {
					transaction_date: row.bill_date,
					from_currency: frm.doc.payable_account_currency,
					to_currency: company_currency
				},
				callback: function (r) {
					frappe.model.set_value(cdt, cdn, 'exchange_rate', r.message);
				}
			});
		}
	},

	get_tax_rate: function(frm, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);

		if (row.item_tax_template) {
			frappe.call({
				method: "erpnext.stock.get_item_details.get_item_tax_map",
				args: {
					company: frm.doc.company,
					item_tax_template: row.item_tax_template
				},
				callback: function (r) {
					if (!r.exc) {
						frappe.model.set_value(cdt, cdn, 'tax_rate', r.message);
					}
				}
			});
		} else {
			frappe.model.set_value(cdt, cdn, 'tax_rate', '{}');
		}
	},

	check_duplicate_bill_no: function (frm, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);

		if (row.bill_no && row.supplier) {
			frappe.call({
				method: "erpnext.accounts.doctype.expense_entry.expense_entry.has_duplicate_bill_no",
				args: {
					bill_no: row.bill_no,
					supplier: row.supplier
				},
				callback: function (r) {
					if (r.message && r.message.length) {
						frappe.msgprint(__("Row {0}: Bill No {1} for Supplier {2} already exists in {3}",
							[row.idx, row.bill_no, row.supplier, r.message.join(", ")]));
					}
				}
			});
		}
	}
});