frappe.provide("erpnext.accounts");

erpnext.accounts.RecordPaymentDialog = class RecordPaymentDialog {
	constructor({ doctype, names, payment_entry, on_save }) {
		this.doctype = doctype;
		this.names = names;
		this.payment_entry = payment_entry;
		this.on_save = on_save;
		this.is_receive = payment_entry.payment_type === "Receive";
		this.bank_field = this.is_receive ? "paid_to" : "paid_from";
		this.party_field = this.is_receive ? "paid_from" : "paid_to";
		this.party_currency = payment_entry[`${this.party_field}_account_currency`];
		this.bank_currency = payment_entry[`${this.bank_field}_account_currency`];
		this.is_multi_currency = this.party_currency !== this.bank_currency;
		this.outstanding = RecordPaymentDialog.total_outstanding(payment_entry.references);
		this.exchange_rate = this.outstanding ? this.get_bank_amount() / this.outstanding : 0;
		this.posting_date = payment_entry.posting_date;
		this.is_refund = payment_entry.references[0].outstanding_amount < 0;
		this.can_deduct = !this.is_refund && !this.is_multi_currency;
		this.can_write_off = this.can_deduct && RecordPaymentDialog.is_invoice(doctype);
		this.deductions = 0;
	}

	static supports(payment_entry) {
		const currencies = [
			payment_entry?.paid_from_account_currency,
			payment_entry?.paid_to_account_currency,
		];
		return Boolean(
			payment_entry?.doctype === "Payment Entry" &&
				["Receive", "Pay"].includes(payment_entry.payment_type) &&
				payment_entry.references?.length &&
				!payment_entry.references.some((row) => row.payment_request) &&
				!payment_entry.deductions?.length &&
				!payment_entry.taxes?.length &&
				!payment_entry.apply_tds &&
				(currencies[0] === currencies[1] ||
					currencies.includes(erpnext.get_currency(payment_entry.company)))
		);
	}

	static async record_from_list(listview) {
		const doctype = listview.doctype;
		const invoices = listview.get_checked_items();
		if (!RecordPaymentDialog.is_one_party(doctype, invoices)) {
			erpnext.bulk_transaction_processing.create(listview, doctype, "Payment Entry");
			return;
		}

		const names = invoices.map((invoice) => invoice.name);
		const payment_entry = await frappe.xcall(
			"erpnext.accounts.doctype.payment_entry.record_payment.get_payment_entry_for",
			{ dt: doctype, names }
		);
		if (!RecordPaymentDialog.supports(payment_entry)) {
			const [doc] = frappe.model.sync(payment_entry);
			frappe.set_route("Form", doc.doctype, doc.name);
			return;
		}
		new RecordPaymentDialog({
			doctype,
			names,
			payment_entry,
			on_save: () => {
				listview.clear_checked_items();
				listview.refresh();
			},
		}).show();
	}

	static is_one_party(doctype, invoices) {
		const [party_field, account_field] =
			doctype === "Sales Invoice" ? ["customer", "debit_to"] : ["supplier", "credit_to"];
		const [first] = invoices;
		return invoices.every(
			(invoice) =>
				invoice.docstatus === 1 &&
				!invoice.is_return &&
				!cint(invoice.on_hold) &&
				flt(invoice.outstanding_amount) > 0 &&
				invoice.company === first.company &&
				invoice[party_field] === first[party_field] &&
				invoice[account_field] === first[account_field]
		);
	}

	static is_invoice(doctype) {
		return ["Sales Invoice", "Purchase Invoice"].includes(doctype);
	}

	static total_outstanding(references) {
		return references.reduce(
			(total, row) => total + Math.abs(RecordPaymentDialog.row_outstanding(row)),
			0
		);
	}

	static row_outstanding(row) {
		return row.payment_term && row.payment_term_outstanding
			? row.payment_term_outstanding
			: row.outstanding_amount;
	}

	async show() {
		await frappe.model.with_doctype("Payment Entry");
		if (this.names.length > 1) await frappe.require("embedded_list.bundle.js");
		this.can_submit =
			frappe.perm.has_perm("Payment Entry", 0, "submit") && !frappe.model.has_workflow("Payment Entry");
		this.set_defaults();
		this.dialog = new frappe.ui.Dialog({
			title: this.get_title(),
			fields: this.get_fields(),
			sheet_on_mobile: true,
			no_submit_on_enter: true,
			primary_action_label: this.can_submit ? __("Submit Payment") : __("Save Draft"),
			primary_action: (values) => this.confirm_save(values),
			secondary_action_label: __("Edit Full Form"),
			secondary_action: () => this.edit_full_form(),
		});
		frappe.ui.button.dress(this.dialog.get_primary_btn(), { variant: "subtle" });
		this.dialog.show();
		this.render_invoices();
		this.refresh_summary();
		this.show_unapplied_credit();
	}

	get_title() {
		const party = this.get_party();
		if (this.is_refund) {
			return this.is_receive ? __("Refund from {0}", [party]) : __("Refund to {0}", [party]);
		}
		return this.is_receive ? __("Payment from {0}", [party]) : __("Payment to {0}", [party]);
	}

	get_submit_question(amount) {
		const args = [format_currency(amount, this.party_currency), this.get_party()];
		if (this.is_refund) {
			return this.is_receive
				? __("Submit a refund of {0} from {1}?", args)
				: __("Submit a refund of {0} to {1}?", args);
		}
		return this.is_receive
			? __("Submit a payment of {0} from {1}?", args)
			: __("Submit a payment of {0} to {1}?", args);
	}

	get_party() {
		return frappe.utils.escape_html(this.payment_entry.party_name || this.payment_entry.party);
	}

	set_defaults() {
		const payment_entry = this.payment_entry;
		this.remembered =
			frappe.get_user_settings("Payment Entry", "record_payment")[this.settings_key()] || {};
		const use_remembered = this.remembered.account && !payment_entry.mode_of_payment;
		this.defaults = use_remembered
			? this.remembered
			: {
					account: payment_entry[this.bank_field],
					account_type: payment_entry[`${this.bank_field}_account_type`],
					mode_of_payment: payment_entry.mode_of_payment,
			  };
		this.account = this.defaults.account;
		this.mode_of_payment = this.defaults.mode_of_payment;
	}

	settings_key() {
		return [this.payment_entry.company, this.payment_entry.payment_type, this.bank_currency].join(":");
	}

	get_fields() {
		return [
			...this.get_payment_fields(),
			...this.get_summary_fields(),
			...this.get_invoice_fields(),
			...this.get_bank_fields(),
			...this.get_deduction_fields(),
			...this.get_email_fields(),
		];
	}

	get_payment_fields() {
		const payment_entry = this.payment_entry;
		return [
			{ fieldname: "party_currency", fieldtype: "Data", hidden: 1, default: this.party_currency },
			{ fieldname: "bank_currency", fieldtype: "Data", hidden: 1, default: this.bank_currency },
			{ fieldname: "account_type", fieldtype: "Data", hidden: 1, default: this.defaults.account_type },
			{
				fieldname: "party_amount",
				fieldtype: "Currency",
				options: "party_currency",
				label: this.is_receive ? __("Amount Received") : __("Amount Paid"),
				reqd: 1,
				default: this.outstanding,
				onchange: () => this.on_amount_change(),
			},
			{
				fieldname: "bank_amount",
				fieldtype: "Currency",
				options: "bank_currency",
				label: __("Amount in {0}", [this.bank_currency]),
				description: this.get_exchange_rate_hint(),
				hidden: !this.is_multi_currency,
				default: this.get_bank_amount(),
				onchange: () => this.refresh_summary(),
			},
			{ fieldtype: "Column Break" },
			{
				fieldname: "posting_date",
				fieldtype: "Date",
				label: __("Posting Date"),
				reqd: 1,
				default: payment_entry.posting_date,
				onchange: () => this.on_posting_date_change(),
			},
		];
	}

	get_invoice_fields() {
		if (this.names.length < 2) return [];
		return [{ fieldtype: "Section Break" }, { fieldname: "invoices", fieldtype: "HTML" }];
	}

	render_invoices() {
		if (this.names.length < 2) return;
		const rows = this.get_invoice_rows();
		new frappe.ui.EmbeddedList({
			wrapper: this.dialog.fields_dict.invoices.$wrapper,
			title: __("Invoices"),
			description: __("The oldest due date is paid first."),
			show_search: rows.length > 5,
			get_data: () => Promise.resolve(rows),
			columns: [
				{
					label: __(this.doctype),
					fieldname: "invoice",
					type: "link",
					route: (row) => ["Form", this.doctype, row.invoice],
				},
				{
					label: __("Due Date"),
					render: (row) => frappe.datetime.str_to_user(row.due_date),
				},
				{
					label: __("Outstanding"),
					align: "right",
					render: (row) => format_currency(row.outstanding_amount, this.party_currency),
				},
			],
		}).refresh();
	}

	get_invoice_rows() {
		const rows = {};
		for (const row of this.payment_entry.references) {
			rows[row.reference_name] ||= {
				invoice: row.reference_name,
				due_date: row.due_date,
				outstanding_amount: 0,
			};
			rows[row.reference_name].outstanding_amount += RecordPaymentDialog.row_outstanding(row);
		}
		return Object.values(rows);
	}

	get_bank_fields() {
		return [
			{ fieldtype: "Section Break" },
			{
				fieldname: "mode_of_payment",
				fieldtype: "Link",
				options: "Mode of Payment",
				label: __("Mode of Payment"),
				default: this.defaults.mode_of_payment,
				onchange: () => this.on_mode_of_payment_change(),
			},
			{
				fieldname: "reference_no",
				fieldtype: "Data",
				label: __("Cheque/Reference No"),
				mandatory_depends_on: "eval:doc.account_type=='Bank'",
			},
			{ fieldtype: "Column Break" },
			{
				fieldname: "account",
				fieldtype: "Link",
				options: "Account",
				label: this.is_receive ? __("Deposit To") : __("Paid From"),
				reqd: 1,
				default: this.defaults.account,
				get_query: () => this.get_account_query(),
				onchange: () => this.on_account_change(),
			},
			{
				fieldname: "reference_date",
				fieldtype: "Date",
				label: __("Cheque/Reference Date"),
				default: this.payment_entry.reference_date,
				mandatory_depends_on: "eval:doc.account_type=='Bank'",
			},
		];
	}

	get_deduction_fields() {
		if (!this.is_receive || !this.can_deduct) return [];
		return [
			{ fieldtype: "Section Break", label: __("Bank Charges and Tax Withheld"), collapsible: 1 },
			{
				fieldname: "bank_charges",
				fieldtype: "Currency",
				options: "party_currency",
				label: __("Bank Charges"),
				onchange: () => this.on_deduction_change(),
			},
			{ fieldtype: "Column Break" },
			{
				fieldname: "tax_withheld",
				fieldtype: "Currency",
				options: "party_currency",
				label: __("Tax Withheld"),
				onchange: () => this.on_deduction_change(),
			},
			{
				fieldname: "tax_withheld_account",
				fieldtype: "Link",
				options: "Account",
				label: __("Tax Withheld Account"),
				default: this.remembered.tax_withheld_account,
				depends_on: "eval:doc.tax_withheld",
				mandatory_depends_on: "eval:doc.tax_withheld",
				get_query: () => ({ filters: { company: this.payment_entry.company, is_group: 0 } }),
			},
		];
	}

	get_summary_fields() {
		return [
			{ fieldtype: "Section Break" },
			{
				fieldname: "outstanding_amount",
				fieldtype: "Currency",
				options: "party_currency",
				label: __("Outstanding Amount"),
				read_only: 1,
				default: this.outstanding,
			},
			{
				fieldname: "write_off",
				fieldtype: "Check",
				hidden: 1,
				onchange: () => this.refresh_summary(),
			},
			{ fieldtype: "Column Break" },
			{
				fieldname: "outstanding_after_payment",
				fieldtype: "Currency",
				options: "party_currency",
				label: __("Outstanding After Payment"),
				read_only: 1,
			},
			{
				fieldname: "advance_amount",
				fieldtype: "Currency",
				options: "party_currency",
				label: __("Kept as Advance"),
				read_only: 1,
				hidden: 1,
			},
		];
	}

	get_email_fields() {
		if (!this.can_email()) return [];
		const email = this.payment_entry.contact_email;
		return [
			{ fieldtype: "Section Break" },
			{
				fieldname: "send_email",
				fieldtype: "Check",
				label: this.is_receive
					? __("Email receipt to {0}", [email])
					: __("Email payment advice to {0}", [email]),
			},
		];
	}

	can_email() {
		return Boolean(
			this.can_submit &&
				!this.is_refund &&
				this.payment_entry.contact_email &&
				frappe.model.can_email("Payment Entry")
		);
	}

	get_account_query() {
		return {
			filters: {
				company: this.payment_entry.company,
				is_group: 0,
				account_type: ["in", ["Bank", "Cash"]],
				account_currency: this.bank_currency,
			},
		};
	}

	get_bank_amount() {
		return this.is_receive ? this.payment_entry.received_amount : this.payment_entry.paid_amount;
	}

	get_exchange_rate() {
		return this.exchange_rate;
	}

	get_exchange_rate_hint() {
		if (!this.is_multi_currency) return "";
		return `1 ${this.party_currency} = ${format_number(this.get_exchange_rate())} ${this.bank_currency}`;
	}

	on_amount_change() {
		if (this.is_multi_currency) {
			const bank_amount = flt(this.dialog.get_value("party_amount")) * this.get_exchange_rate();
			this.dialog.set_value("bank_amount", flt(bank_amount, this.get_precision()));
		}
		this.refresh_summary();
	}

	async on_posting_date_change() {
		const posting_date = this.dialog.get_value("posting_date");
		if (!this.is_multi_currency || !posting_date || posting_date === this.posting_date) return;
		this.posting_date = posting_date;
		const rate = await frappe.xcall("erpnext.setup.utils.get_exchange_rate", {
			from_currency: this.party_currency,
			to_currency: this.bank_currency,
			transaction_date: posting_date,
		});
		if (!rate || this.dialog.get_value("posting_date") !== posting_date) return;
		this.exchange_rate = rate;
		this.dialog.set_df_property("bank_amount", "description", this.get_exchange_rate_hint());
		this.on_amount_change();
	}

	on_deduction_change() {
		const precision = this.get_precision();
		const amount = flt(this.dialog.get_value("party_amount"));
		const was_paid_in_full =
			flt(amount + this.deductions, precision) === flt(this.outstanding, precision);
		this.deductions = this.get_deductions();
		if (was_paid_in_full) {
			this.dialog.set_value("party_amount", flt(this.outstanding - this.deductions, precision));
		} else {
			this.refresh_summary();
		}
	}

	get_deductions() {
		return flt(this.dialog.get_value("bank_charges")) + flt(this.dialog.get_value("tax_withheld"));
	}

	async on_mode_of_payment_change() {
		const mode_of_payment = this.dialog.get_value("mode_of_payment");
		if (!mode_of_payment || mode_of_payment === this.mode_of_payment) return;
		this.mode_of_payment = mode_of_payment;
		const bank = await frappe.xcall(
			"erpnext.accounts.doctype.sales_invoice.sales_invoice.get_bank_cash_account",
			{ mode_of_payment, company: this.payment_entry.company }
		);
		if (bank?.account) {
			this.dialog.set_value("account", bank.account);
		}
	}

	async on_account_change() {
		const account = this.dialog.get_value("account");
		if (!account || account === this.account) return;
		this.account = account;
		const { message } = await frappe.db.get_value("Account", account, [
			"account_type",
			"account_currency",
		]);
		if (this.dialog.get_value("account") !== account) return;

		if (message.account_currency !== this.bank_currency) {
			this.dialog.set_value("account", this.payment_entry[this.bank_field]);
			frappe.msgprint(
				__(
					"{0} is a {1} account. Use Edit Full Form to pay through an account in another currency.",
					[account.bold(), message.account_currency]
				)
			);
			return;
		}
		this.dialog.set_value("account_type", message.account_type);
		this.dialog.refresh_dependency();
	}

	refresh_summary() {
		const precision = this.get_precision();
		const settled = flt(this.dialog.get_value("party_amount")) + this.get_deductions();
		const remaining = flt(this.outstanding - settled, precision);
		this.refresh_write_off(remaining);

		const written_off = remaining > 0 && this.dialog.get_value("write_off");
		this.dialog.set_value("outstanding_after_payment", written_off ? 0 : Math.max(remaining, 0));

		const advance = this.is_refund ? 0 : Math.max(-remaining, 0);
		this.dialog.set_value("advance_amount", advance);
		this.dialog.set_df_property("advance_amount", "hidden", !advance);
	}

	refresh_write_off(remaining) {
		const can_write_off = this.can_write_off && remaining > 0;
		this.dialog.set_df_property("write_off", "hidden", !can_write_off);
		this.dialog.set_df_property(
			"write_off",
			"label",
			__("Write off the remaining {0}", [format_currency(remaining, this.party_currency)])
		);
		if (!can_write_off && this.dialog.get_value("write_off")) {
			this.dialog.set_value("write_off", 0);
		}
	}

	async show_unapplied_credit() {
		if (this.is_refund || !RecordPaymentDialog.is_invoice(this.doctype)) return;
		const credit = await frappe.xcall(
			"erpnext.accounts.doctype.payment_entry.record_payment.get_unapplied_credit",
			{ dt: this.doctype, dn: this.names[0] }
		);
		if (!credit) return;

		const amount = format_currency(credit, this.party_currency);
		frappe.ui
			.alert({
				theme: "blue",
				title:
					this.payment_entry.party_type === "Customer"
						? __("This customer has {0} in unapplied payments and credit notes.", [amount])
						: __("This supplier has {0} in unapplied payments and debit notes.", [amount]),
				primary_action: { label: __("Reconcile"), onclick: () => this.open_reconciliation() },
			})
			.prependTo(this.dialog.body);
	}

	open_reconciliation() {
		const { company, party_type, party } = this.payment_entry;
		this.dialog.hide();
		frappe.route_options = { company, party_type, party };
		frappe.set_route("Form", "Payment Reconciliation");
	}

	get_precision() {
		return precision("paid_amount", this.payment_entry);
	}

	confirm_save(values) {
		if (!this.can_submit) return this.save(values);
		frappe.confirm(this.get_submit_question(values.party_amount), () => this.save(values));
	}

	async save(values) {
		const payment_entry = await this.record_payment(values, true);
		this.remember(values);
		this.dialog.hide();
		this.show_result(payment_entry);
		this.on_save();
	}

	remember(values) {
		frappe.model.user_settings.save("Payment Entry", "record_payment", {
			[this.settings_key()]: {
				account: values.account,
				account_type: values.account_type,
				mode_of_payment: values.mode_of_payment || null,
				tax_withheld_account:
					values.tax_withheld_account || this.remembered.tax_withheld_account || null,
			},
		});
	}

	show_result(payment_entry) {
		const link = frappe.utils.get_form_link("Payment Entry", payment_entry.name, true);
		frappe.show_alert({
			message:
				payment_entry.docstatus === 1
					? __("Payment {0} submitted", [link])
					: __("Draft {0} saved", [link]),
			indicator: "green",
		});
	}

	async edit_full_form() {
		const payment_entry = await this.record_payment(this.dialog.get_values(true), false);
		this.dialog.hide();
		const [doc] = frappe.model.sync(payment_entry);
		frappe.set_route("Form", doc.doctype, doc.name);
	}

	async record_payment(values, save) {
		const { message } = await frappe.call({
			method: "erpnext.accounts.doctype.payment_entry.record_payment.record_payment",
			args: { dt: this.doctype, names: this.names, values, save },
			freeze: true,
		});
		return message;
	}
};
