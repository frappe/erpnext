frappe.provide("erpnext.accounts.bank_reconciliation");

erpnext.accounts.bank_reconciliation.CreateTab = class CreateTab {
	constructor(opts) {
		Object.assign(this, opts);
		this.make();
	}

	make() {
		this.panel_manager.actions_tab = "create_voucher-tab";

		this.create_field_group = new frappe.ui.FieldGroup({
			fields: this.get_create_tab_fields(),
			body: this.actions_panel.$tab_content,
			card_layout: true,
		});
		this.create_field_group.make();
	}

	create_voucher() {
		var me = this;
		let values = this.create_field_group.get_values();
		let document_type = values.document_type;

		// Create new voucher and delete or refresh current BT row depending on reconciliation
		this.create_voucher_bts(
			null,
			(message) => me.actions_panel.after_transaction_reconcile(
				message, true, document_type
			)
		)
	}

	edit_in_full_page() {
		this.create_voucher_bts(true, (message) => {
			const doc = frappe.model.sync(message);
			frappe.open_in_new_tab = true;
			frappe.set_route("Form", doc[0].doctype, doc[0].name);
		});
	}

	create_voucher_bts(allow_edit=false, success_callback) {
		// Create PE or JV and run `success_callback`
		let values = this.create_field_group.get_values();
		let document_type = values.document_type;
		let method = "erpnext.accounts.doctype.bank_reconciliation_tool_beta.bank_reconciliation_tool_beta";
		let args = {
			bank_transaction_name: this.transaction.name,
			reference_number: values.reference_number,
			reference_date: values.reference_date,
			party_type: values.party_type,
			party: values.party,
			posting_date: values.posting_date,
			mode_of_payment: values.mode_of_payment,
			allow_edit: allow_edit
		};

		if (document_type === "Payment Entry") {
			method = method + ".create_payment_entry_bts";
			args = {
				...args,
				project: values.project,
				cost_center: values.cost_center
			}
		} else {
			method =  method + ".create_journal_entry_bts";
			args = {
				...args,
				entry_type: values.journal_entry_type,
				second_account: values.second_account,
			}
		}

		frappe.call({
			method: method,
			args: args,
			callback: (response) => {
				if (response.exc) {
					frappe.show_alert({
						message: __("Failed to create {0} against {1}", [document_type, this.transaction.name]),
						indicator: "red"
					});
					return;
				} else if (response.message) {
					success_callback(response.message);
				}
			}
		})

	}

	get_create_tab_fields() {
		let party_type = this.transaction.party_type || (flt(this.transaction.withdrawal) > 0 ? "Supplier" : "Customer");
		return [
			{
				label: __("Document Type"),
				fieldname: "document_type",
				fieldtype: "Select",
				options: `Payment Entry\nJournal Entry`,
				default: "Payment Entry",
				onchange: () => {
					let value = this.create_field_group.get_value("document_type");
					let fields = this.create_field_group;

					fields.get_field("journal_entry_type").df.reqd = value === "Journal Entry";
					fields.get_field("second_account").df.reqd = value === "Journal Entry";

					this.create_field_group.refresh();
				}
			},
			{
				fieldtype: "Section Break",
				fieldname: "details",
				label: "Details",
			},
			{
				fieldname: "reference_number",
				fieldtype: "Data",
				label: __("Reference Number"),
				default: this.transaction.reference_number || this.transaction.description.slice(0, 140),
			},
			{
				fieldname: "posting_date",
				fieldtype: "Date",
				label: __("Posting Date"),
				reqd: 1,
				default: this.transaction.date,
			},
			{
				fieldname: "reference_date",
				fieldtype: "Date",
				label: __("Cheque/Reference Date"),
				reqd: 1,
				default: this.transaction.date,
			},
			{
				fieldname: "mode_of_payment",
				fieldtype: "Link",
				label: __("Mode of Payment"),
				options: "Mode of Payment",
			},
			{
				fieldname: "edit_in_full_page",
				fieldtype: "Button",
				label: __("Edit in Full Page"),
				click: () => {
					this.edit_in_full_page();
				},
			},
			{
				fieldname: "column_break_7",
				fieldtype: "Column Break",
			},
			{
				label: __("Journal Entry Type"),
				fieldname: "journal_entry_type",
				fieldtype: "Select",
				options:
				`Bank Entry\nJournal Entry\nInter Company Journal Entry\nCash Entry\nCredit Card Entry\nDebit Note\nCredit Note\nContra Entry\nExcise Entry\nWrite Off Entry\nOpening Entry\nDepreciation Entry\nExchange Rate Revaluation\nDeferred Revenue\nDeferred Expense`,
				default: "Bank Entry",
				depends_on: "eval: doc.document_type == 'Journal Entry'",
			},
			{
				fieldname: "second_account",
				fieldtype: "Link",
				label: "Account",
				options: "Account",
				get_query: () => {
					return {
						filters: {
							is_group: 0,
							company: this.company,
						},
					};
				},
				depends_on: "eval: doc.document_type == 'Journal Entry'",
			},
			{
				fieldname: "party_type",
				fieldtype: "Link",
				label: "Party Type",
				options: "DocType",
				reqd: 1,
				default: party_type,
				get_query: function () {
					return {
						filters: {
							name: [
								"in",
								Object.keys(frappe.boot.party_account_types),
							],
						},
					};
				},
				onchange: () => {
					let value = this.create_field_group.get_value("party_type");
					this.create_field_group.get_field("party").df.options = value;
				}
			},
			{
				fieldname: "party",
				fieldtype: "Link",
				label: "Party",
				default: this.transaction.party,
				options: party_type,
				reqd: 1,
			},
			{
				fieldname: "project",
				fieldtype: "Link",
				label: "Project",
				options: "Project",
				depends_on: "eval: doc.document_type == 'Payment Entry'",
			},
			{
				fieldname: "cost_center",
				fieldtype: "Link",
				label: "Cost Center",
				options: "Cost Center",
				depends_on: "eval: doc.document_type == 'Payment Entry'",
			},
			{
				fieldtype: "Section Break"
			},
			{
				label: __("Hidden field for alignment"),
				fieldname: "hidden_field",
				fieldtype: "Data",
				hidden: 1
			},
			{
				fieldtype: "Column Break"
			},
			{
				label: __("Create"),
				fieldtype: "Button",
				primary: true,
				click: () => this.create_voucher(),
			}
		];
	}
}