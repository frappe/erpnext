// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.accounts");
frappe.provide("erpnext.journal_entry");

frappe.ui.form.on("Journal Entry", {
	setup(frm) {
		frm.ignore_doctypes_on_cancel_all = [
			"Sales Invoice",
			"Purchase Invoice",
			"Journal Entry",
			"Repost Payment Ledger",
			"Asset",
			"Asset Movement",
			"Asset Depreciation Schedule",
			"Repost Accounting Ledger",
			"Unreconcile Payment",
			"Unreconcile Payment Entries",
			"Bank Transaction",
		];
	},

	onload(frm) {
		erpnext.journal_entry.load_defaults(frm);
		erpnext.journal_entry.setup_queries(frm);
		erpnext.accounts.dimensions.setup_dimension_filters(frm, frm.doctype);
	},

	refresh(frm) {
		if (frm.doc.reversal_of && (frm.is_new() || frm.doc.docstatus == 0)) {
			erpnext.journal_entry.lock_reversal_entry(frm);
		}

		erpnext.toggle_naming_series();
		erpnext.journal_entry.add_custom_buttons(frm);
		erpnext.journal_entry.toggle_fields_based_on_currency(frm);
		erpnext.accounts.unreconcile_payment.add_unreconcile_btn(frm);

		if (frm.doc.voucher_type !== "Exchange Gain Or Loss") {
			(frm.doc.accounts || []).forEach((row) =>
				erpnext.journal_entry.set_exchange_rate(frm, row.doctype, row.name)
			);
		}
	},

	before_save(frm) {
		if (frm.doc.docstatus != 0 || frm.doc.is_system_generated) return;

		const manual_payment_references = frm.doc.accounts.filter(
			(row) => row.reference_type == "Payment Entry"
		);
		if (manual_payment_references.length) {
			const rows = manual_payment_references.map((row) => "#" + row.idx);
			frappe.throw(
				__("Rows: {0} have 'Payment Entry' as reference_type. This should not be set manually.", [
					frappe.utils.comma_and(rows),
				])
			);
		}
	},

	company(frm) {
		frappe.db.get_value("Company", frm.doc.company, "cost_center").then(({ message }) => {
			if (!message) return;
			(frm.doc.accounts || []).forEach((row) =>
				frappe.model.set_value(row.doctype, row.name, "cost_center", message.cost_center)
			);
		});

		erpnext.accounts.dimensions.update_dimension(frm, frm.doctype);
		erpnext.utils.set_letter_head(frm);
		frm.clear_table("tax_withholding_entries");
	},

	voucher_type(frm) {
		if (!frm.doc.company) return;

		const accounts = frm.doc.accounts || [];
		const has_account = accounts.length && !(accounts.length === 1 && !accounts[0].account);
		if (has_account || !["Bank Entry", "Cash Entry"].includes(frm.doc.voucher_type)) return;

		return frappe.call({
			method: "erpnext.accounts.doctype.journal_entry.journal_entry.get_default_bank_cash_account",
			args: {
				account_type: frm.doc.voucher_type == "Bank Entry" ? "Bank" : "Cash",
				company: frm.doc.company,
			},
			callback: ({ message }) => {
				if (message && !$.isEmptyObject(message)) {
					erpnext.journal_entry.update_jv_details(frm, [message]);
				}
			},
		});
	},

	posting_date(frm) {
		if (!frm.doc.multi_currency || !frm.doc.posting_date) return;

		(frm.doc.accounts || []).forEach((row) =>
			erpnext.journal_entry.set_exchange_rate(frm, row.doctype, row.name)
		);
	},

	multi_currency(frm) {
		erpnext.journal_entry.toggle_fields_based_on_currency(frm);
	},

	from_template(frm) {
		if (!frm.doc.from_template) return;

		frappe.db.get_doc("Journal Entry Template", frm.doc.from_template).then((template) => {
			frappe.model.clear_table(frm.doc, "accounts");
			frm.set_value({
				company: template.company,
				voucher_type: template.voucher_type,
				naming_series: template.naming_series,
				is_opening: template.is_opening,
				multi_currency: template.multi_currency,
			});
			erpnext.journal_entry.update_jv_details(frm, template.accounts);
		});
	},

	apply_tds(frm) {
		frm.clear_table("tax_withholding_entries");
	},

	get_balance(frm) {
		erpnext.journal_entry.update_totals(frm);
		frm.call("get_balance", {}, () => frm.refresh());
	},

	get_balance_for_periodic_accounting(frm) {
		frm.call({
			method: "get_balance_for_periodic_accounting",
			doc: frm.doc,
			callback: () => frm.refresh_field("accounts"),
		});
	},
});

frappe.ui.form.on("Journal Entry Account", {
	party(frm, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);
		if (row.account || !row.party_type || !row.party) return;

		if (!frm.doc.company) frappe.throw(__("Please select Company"));
		return frm.call({
			method: "erpnext.accounts.doctype.journal_entry.journal_entry.get_party_account_and_currency",
			child: row,
			args: { company: frm.doc.company, party_type: row.party_type, party: row.party },
		});
	},

	account(frm, cdt, cdn) {
		erpnext.journal_entry.set_account_details(frm, cdt, cdn);
	},

	debit_in_account_currency(frm, cdt, cdn) {
		erpnext.journal_entry.set_exchange_rate(frm, cdt, cdn);
	},

	credit_in_account_currency(frm, cdt, cdn) {
		erpnext.journal_entry.set_exchange_rate(frm, cdt, cdn);
	},

	debit(frm) {
		erpnext.journal_entry.update_totals(frm);
	},

	credit(frm) {
		erpnext.journal_entry.update_totals(frm);
	},

	exchange_rate(frm, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);
		const company_currency = erpnext.get_currency(frm.doc.company);
		if (row.account_currency == company_currency || !frm.doc.multi_currency) {
			frappe.model.set_value(cdt, cdn, "exchange_rate", 1);
		}
		erpnext.journal_entry.set_debit_credit_in_company_currency(frm, cdt, cdn);
	},

	reference_name(frm, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);
		if (!row.reference_name) return;

		if (row.reference_type === "Purchase Invoice" && !flt(row.debit)) {
			erpnext.journal_entry.get_outstanding(frm, "Purchase Invoice", row.reference_name, row);
		} else if (row.reference_type === "Sales Invoice" && !flt(row.credit)) {
			erpnext.journal_entry.get_outstanding(frm, "Sales Invoice", row.reference_name, row);
		} else if (row.reference_type === "Journal Entry" && !flt(row.credit) && !flt(row.debit)) {
			erpnext.journal_entry.get_outstanding(frm, "Journal Entry", row.reference_name, row);
		}
	},

	accounts_add(frm, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);
		if (!row.exchange_rate) row.exchange_rate = 1;

		if (!row.account) {
			(frm.doc.accounts || []).forEach((d) => {
				if (d.account && d.party && d.party_type) {
					row.account = d.account;
					row.party = d.party;
					row.party_type = d.party_type;
					row.exchange_rate = d.exchange_rate;
				}
			});
		}

		erpnext.journal_entry.set_balancing_amount(row, frm.doc.difference);
		erpnext.journal_entry.update_totals(frm);
		erpnext.accounts.dimensions.copy_dimension_from_first_row(frm, cdt, cdn, "accounts");
	},

	accounts_remove(frm) {
		erpnext.journal_entry.update_totals(frm);
	},
});

Object.assign(erpnext.journal_entry, {
	load_defaults(frm) {
		if (!(frm.doc.__islocal && frm.doc.company)) return;

		frappe.model.set_default_values(frm.doc);
		(frm.doc.accounts || []).forEach((row) => frappe.model.set_default_values(row));

		if (!frm.doc.amended_from) {
			frm.set_value("posting_date", frm.doc.posting_date || frappe.datetime.get_today());
		}
	},

	lock_reversal_entry(frm) {
		frm.fields
			.filter((field) => field.has_input)
			.forEach((field) => frm.set_df_property(field.df.fieldname, "read_only", 1));
		frm.set_df_property("accounts", "read_only", 1);
	},

	add_custom_buttons(frm) {
		if (frm.doc.docstatus > 0) {
			frm.add_custom_button(
				__("Ledger"),
				() => erpnext.journal_entry.show_general_ledger(frm),
				__("View")
			);
		}

		if (frm.doc.docstatus == 1) {
			frm.add_custom_button(
				__("Reverse Journal Entry"),
				() => erpnext.journal_entry.reverse_journal_entry(frm),
				__("Actions")
			);
		}

		if (frm.doc.__islocal) {
			frm.add_custom_button(__("Quick Entry"), () => erpnext.journal_entry.quick_entry(frm));
		}

		if (
			frm.doc.voucher_type == "Inter Company Journal Entry" &&
			frm.doc.docstatus == 1 &&
			!frm.doc.inter_company_journal_entry_reference
		) {
			frm.add_custom_button(
				__("Create Inter Company Journal Entry"),
				() => erpnext.journal_entry.make_inter_company_journal_entry(frm),
				__("Make")
			);
		}
	},

	show_general_ledger(frm) {
		frappe.route_options = {
			voucher_no: frm.doc.name,
			from_date: frm.doc.posting_date,
			to_date: moment(frm.doc.modified).format("YYYY-MM-DD"),
			company: frm.doc.company,
			finance_book: frm.doc.finance_book,
			categorize_by: "",
			show_cancelled_entries: frm.doc.docstatus === 2,
		};
		frappe.set_route("query-report", "General Ledger");
	},

	make_inter_company_journal_entry(frm) {
		const dialog = new frappe.ui.Dialog({
			title: __("Select Company"),
			fields: [
				{
					fieldname: "company",
					fieldtype: "Link",
					label: __("Company"),
					options: "Company",
					reqd: 1,
					get_query: () => {
						return { filters: [["Company", "name", "!=", frm.doc.company]] };
					},
				},
			],
		});

		dialog.set_primary_action(__("Create"), () => {
			dialog.hide();
			frappe.call({
				method: "erpnext.accounts.doctype.journal_entry.mapper.make_inter_company_journal_entry",
				args: {
					name: frm.doc.name,
					voucher_type: frm.doc.voucher_type,
					company: dialog.get_value("company"),
				},
				callback: ({ message }) => {
					if (message) {
						const doc = frappe.model.sync(message)[0];
						frappe.set_route("Form", doc.doctype, doc.name);
					}
				},
			});
		});
		dialog.show();
	},

	reverse_journal_entry(frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.accounts.doctype.journal_entry.mapper.make_reverse_journal_entry",
			frm: frm,
		});
	},

	quick_entry(frm) {
		const naming_series_options = frm.fields_dict.naming_series.df.options;
		const naming_series_default =
			frm.fields_dict.naming_series.df.default || naming_series_options.split("\n")[0];

		const dialog = new frappe.ui.Dialog({
			title: __("Quick Journal Entry"),
			fields: [
				{ fieldtype: "Currency", fieldname: "debit", label: __("Amount"), reqd: 1 },
				{
					fieldtype: "Link",
					fieldname: "debit_account",
					label: __("Debit Account"),
					reqd: 1,
					options: "Account",
					get_query: () => erpnext.journal_entry.account_query(frm),
				},
				{
					fieldtype: "Link",
					fieldname: "credit_account",
					label: __("Credit Account"),
					reqd: 1,
					options: "Account",
					get_query: () => erpnext.journal_entry.account_query(frm),
				},
				{
					fieldtype: "Date",
					fieldname: "posting_date",
					label: __("Date"),
					reqd: 1,
					default: frm.doc.posting_date,
				},
				{ fieldtype: "Small Text", fieldname: "remark", label: __("Remark") },
				{
					fieldtype: "Select",
					fieldname: "naming_series",
					label: __("Series"),
					reqd: 1,
					options: naming_series_options,
					default: naming_series_default,
				},
			],
		});

		dialog.set_primary_action(__("Save"), () => {
			erpnext.journal_entry.save_quick_entry(frm, dialog.get_values());
			dialog.hide();
		});
		dialog.show();
	},

	save_quick_entry(frm, values) {
		frm.set_value("posting_date", values.posting_date);
		frm.set_value("naming_series", values.naming_series);
		frm.set_value("custom_remark", values.remark ? 1 : 0);
		frm.set_value("remark", values.remark || "");

		// clear table in case a previous add left a partially populated row behind
		frm.clear_table("accounts");

		// grid.add_new_row() adds the row in the UI as well as locals, which the triggers need
		erpnext.journal_entry.add_quick_entry_row(
			frm,
			values.debit_account,
			"debit_in_account_currency",
			values.debit
		);
		erpnext.journal_entry.add_quick_entry_row(
			frm,
			values.credit_account,
			"credit_in_account_currency",
			values.debit
		);

		frm.save();
	},

	add_quick_entry_row(frm, account, amount_field, amount) {
		const row = frm.fields_dict.accounts.grid.add_new_row();
		frappe.model.set_value(row.doctype, row.name, "account", account);
		frappe.model.set_value(row.doctype, row.name, amount_field, amount);
	},

	get_outstanding(frm, reference_type, reference_name, child) {
		return frappe.call({
			method: "erpnext.accounts.doctype.journal_entry.journal_entry.get_outstanding",
			args: {
				doctype: reference_type,
				docname: reference_name,
				company: frm.doc.company,
				account: child.account,
				party: child.party,
				account_currency: child.account_currency,
			},
			callback: ({ message }) => {
				if (!message) return;
				Object.entries(message).forEach(([field, value]) =>
					frappe.model.set_value(child.doctype, child.name, field, value)
				);
			},
		});
	},

	set_account_details(frm, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);
		if (!row.account) {
			erpnext.journal_entry.clear_fields(frm, cdt, cdn);
			return;
		}
		if (!frm.doc.company) frappe.throw(__("Please select Company first"));
		if (!frm.doc.posting_date) frappe.throw(__("Please select Posting Date first"));

		return frappe.call({
			method: "erpnext.accounts.doctype.journal_entry.journal_entry.get_account_details_and_party_type",
			args: {
				account: row.account,
				date: frm.doc.posting_date,
				company: frm.doc.company,
				debit: flt(row.debit_in_account_currency),
				credit: flt(row.credit_in_account_currency),
				exchange_rate: row.exchange_rate,
			},
			callback: ({ message }) => {
				if (!message) return;
				$.extend(row, message);
				erpnext.journal_entry.set_amount_on_last_row(frm, cdt, cdn);
				erpnext.journal_entry.set_debit_credit_in_company_currency(frm, cdt, cdn);
				frm.refresh_field("accounts");
			},
		});
	},

	set_amount_on_last_row(frm, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);
		if (row.idx != frm.doc.accounts.length) return;

		const difference = frm.doc.accounts.reduce((total, account) => {
			return account.idx == row.idx ? total : total + account.debit - account.credit;
		}, 0);
		erpnext.journal_entry.set_balancing_amount(row, difference);
	},

	set_balancing_amount(row, difference) {
		if (!difference) return;

		const exchange_rate = row.exchange_rate || 1;
		if (difference > 0) {
			row.credit_in_account_currency = difference / exchange_rate;
			row.credit = difference;
		} else {
			row.debit_in_account_currency = -difference / exchange_rate;
			row.debit = -difference;
		}
	},

	clear_fields(frm, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);
		row.party_type = null;
		row.party = null;
		row.bank_account = null;
		frm.refresh_field("accounts");
	},

	setup_queries(frm) {
		frm.set_query("periodic_entry_difference_account", () => {
			return { filters: { is_group: 0, company: frm.doc.company } };
		});

		frm.set_query("stock_asset_account", () => {
			return { filters: { is_group: 0, account_type: "Stock", company: frm.doc.company } };
		});

		frm.set_query("project", "accounts", (doc, cdt, cdn) => {
			const row = frappe.get_doc(cdt, cdn);
			const filters = { company: doc.company };
			if (row.party_type == "Customer") filters.customer = row.party;
			return { query: "erpnext.controllers.queries.get_project_name", filters };
		});

		frm.set_query("account", "accounts", () => erpnext.journal_entry.account_query(frm));

		frm.set_query("party_type", "accounts", (doc, cdt, cdn) => {
			return {
				query: "erpnext.setup.doctype.party_type.party_type.get_party_type",
				filters: { account: frappe.get_doc(cdt, cdn).account },
			};
		});

		frm.set_query("reference_name", "accounts", (doc, cdt, cdn) => {
			return erpnext.journal_entry.reference_name_query(frappe.get_doc(cdt, cdn));
		});
	},

	reference_name_query(row) {
		if (row.reference_type === "Journal Entry") {
			frappe.model.validate_missing(row, "account");
			return {
				query: "erpnext.accounts.doctype.journal_entry.journal_entry.get_against_jv",
				filters: { account: row.account, party: row.party },
			};
		}

		const out = { filters: [[row.reference_type, "docstatus", "=", 1]] };

		if (["Sales Invoice", "Purchase Invoice"].includes(row.reference_type)) {
			out.filters.push([row.reference_type, "outstanding_amount", "!=", 0]);
			if (row.cost_center) {
				out.filters.push([row.reference_type, "cost_center", "in", ["", row.cost_center]]);
			}
			frappe.model.validate_missing(row, "account");
			const party_account_field = row.reference_type === "Sales Invoice" ? "debit_to" : "credit_to";
			out.filters.push([row.reference_type, party_account_field, "=", row.account]);
		}

		if (["Sales Order", "Purchase Order"].includes(row.reference_type)) {
			frappe.model.validate_missing(row, "party_type");
			frappe.model.validate_missing(row, "party");
			out.filters.push([row.reference_type, "per_billed", "<", 100]);
		}

		if (row.party_type && row.party) {
			let party_field = "";
			if (row.reference_type.indexOf("Sales") === 0) {
				party_field = "customer";
			} else if (row.reference_type.indexOf("Purchase") === 0) {
				party_field = "supplier";
			}
			if (party_field) out.filters.push([row.reference_type, party_field, "=", row.party]);
		}

		return out;
	},

	account_query(frm) {
		const filters = { company: frm.doc.company, is_group: 0 };
		if (!frm.doc.multi_currency) {
			const company_currency = erpnext.get_currency(frm.doc.company);
			filters.account_currency = ["in", [company_currency, null]];
		}
		return { filters };
	},

	toggle_fields_based_on_currency(frm) {
		const fields = ["currency_section", "account_currency", "exchange_rate", "debit", "credit"];
		const grid = frm.get_field("accounts").grid;
		if (!grid) return;

		grid.set_column_disp(fields, frm.doc.multi_currency);

		const field_label_map = {
			debit_in_account_currency: "Debit",
			credit_in_account_currency: "Credit",
		};
		Object.entries(field_label_map).forEach(([fieldname, label]) => {
			grid.update_docfield_property(
				fieldname,
				"label",
				frm.doc.multi_currency ? label + " in Account Currency" : label
			);
		});
	},

	update_jv_details(frm, rows) {
		rows.forEach((source) => {
			const row = frappe.model.add_child(frm.doc, "Journal Entry Account", "accounts");
			const {
				idx,
				name,
				owner,
				parent,
				parenttype,
				parentfield,
				creation,
				modified,
				modified_by,
				doctype,
				docstatus,
				...fields
			} = source;
			frappe.model.set_value(row.doctype, row.name, fields);
		});
		frm.refresh_field("accounts");
		erpnext.journal_entry.update_totals(frm);
	},

	update_totals(frm) {
		let total_debit = 0;
		let total_credit = 0;
		(frm.doc.accounts || []).forEach((row) => {
			total_debit += flt(row.debit, precision("debit", row));
			total_credit += flt(row.credit, precision("credit", row));
		});

		frm.doc.total_debit = total_debit;
		frm.doc.total_credit = total_credit;
		frm.doc.difference = flt(total_debit - total_credit, precision("difference"));
		["total_debit", "total_credit", "difference"].forEach((field) => frm.refresh_field(field));
	},

	set_debit_credit_in_company_currency(frm, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);
		frappe.model.set_value(
			cdt,
			cdn,
			"debit",
			flt(flt(row.debit_in_account_currency) * row.exchange_rate, precision("debit", row))
		);
		frappe.model.set_value(
			cdt,
			cdn,
			"credit",
			flt(flt(row.credit_in_account_currency) * row.exchange_rate, precision("credit", row))
		);
		erpnext.journal_entry.update_totals(frm);
	},

	set_exchange_rate(frm, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);
		const company_currency = erpnext.get_currency(frm.doc.company);

		if (row.account_currency == company_currency || !frm.doc.multi_currency) {
			row.exchange_rate = 1;
			erpnext.journal_entry.set_debit_credit_in_company_currency(frm, cdt, cdn);
		} else if (!row.exchange_rate || row.exchange_rate == 1 || row.account_type == "Bank") {
			frappe.call({
				method: "erpnext.accounts.doctype.journal_entry.journal_entry.get_exchange_rate",
				args: {
					posting_date: frm.doc.posting_date,
					account: row.account,
					account_currency: row.account_currency,
					company: frm.doc.company,
					reference_type: cstr(row.reference_type),
					reference_name: cstr(row.reference_name),
					debit: flt(row.debit_in_account_currency),
					credit: flt(row.credit_in_account_currency),
					exchange_rate: row.exchange_rate,
				},
				callback: ({ message }) => {
					if (!message) return;
					row.exchange_rate = message;
					erpnext.journal_entry.set_debit_credit_in_company_currency(frm, cdt, cdn);
				},
			});
		} else {
			erpnext.journal_entry.set_debit_credit_in_company_currency(frm, cdt, cdn);
		}
		frm.refresh_field("accounts");
	},
});
