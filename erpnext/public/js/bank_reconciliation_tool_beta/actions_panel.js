frappe.provide("erpnext.accounts.bank_reconciliation");

erpnext.accounts.bank_reconciliation.ActionsPanel = class ActionsPanel {
	constructor(opts) {
		Object.assign(this, opts);
		this.make();
	}

	make() {
		this.init_actions_container();
		this.render_tabs();

		// Default to last selected tab
		this.$actions_container.find("#" + this.panel_manager.actions_tab).trigger("click");
	}

	init_actions_container() {
		if (this.$wrapper.find(".actions-panel").length > 0) {
			this.$actions_container = this.$wrapper.find(".actions-panel");
			this.$actions_container.empty();
		} else {
			this.$actions_container = this.$wrapper.append(`
				<div class="actions-panel"></div>
			`).find(".actions-panel");
		}

		this.$actions_container.append(`
			<div class="form-tabs-list">
				<ul class="nav form-tabs" role="tablist" aria-label="Action Tabs">
				</ul>
			</div>

			<div class="tab-content p-10"></div>
		`);
	}

	render_tabs() {
		this.tabs_list_ul = this.$actions_container.find(".form-tabs");
		this.$tab_content = this.$actions_container.find(".tab-content");

		["Details", "Match Voucher", "Create Voucher"].forEach(tab => {
			let tab_name = frappe.scrub(tab);
			this.add_tab(tab_name, tab);

			let $tab_link = this.tabs_list_ul.find(`#${tab_name}-tab`);
			$tab_link.on("click", () => {
				if (tab == "Details") {
					this.details_section();
				} else if (tab == "Match Voucher") {
					this.render_match_section();
				} else {
					this.create_section();
				}
			});
		});
	}

	add_tab(tab_name, tab) {
		this.tabs_list_ul.append(`
			<li class="nav-item">
				<a class="nav-actions-link"
					id="${tab_name}-tab" data-toggle="tab"
					href="#" role="tab" aria-controls="${tab}"
				>
					${__(tab)}
				</a>
			</li>
		`);
	}

	details_section() {
		this.$tab_content.empty();
		this.panel_manager.actions_tab = "details-tab";

		this.details_field_group = new frappe.ui.FieldGroup({
			fields: this.get_detail_tab_fields(),
			body: this.$tab_content,
			card_layout: true,
		});
		this.details_field_group.make();
	}

	create_section() {
		this.$tab_content.empty();
		this.panel_manager.actions_tab = "create_voucher-tab";

		this.create_field_group = new frappe.ui.FieldGroup({
			fields: this.get_create_tab_fields(),
			body: this.$tab_content,
			card_layout: true,
		});
		this.create_field_group.make();
	}

	async render_match_section() {
		this.$tab_content.empty();
		this.panel_manager.actions_tab = "match_voucher-tab";

		this.match_field_group = new frappe.ui.FieldGroup({
			fields: this.get_match_tab_fields(),
			body: this.$tab_content,
			card_layout: true,
		});
		this.match_field_group.make()

		this.summary_empty_state();
		await this.populate_matching_vouchers();
	}

	summary_empty_state() {
		let summary_field = this.match_field_group.get_field("transaction_amount_summary").$wrapper;
		summary_field.append(
			`<div class="report-summary reconciliation-summary" style="height: 90px;">
			</div>`
		);
	}

	async populate_matching_vouchers() {
		let filter_fields = this.match_field_group.get_values();
		let document_types = Object.keys(filter_fields).filter(field => filter_fields[field] === 1);

		this.update_filters_in_state(document_types);

		let vouchers = await this.get_matching_vouchers(document_types);
		this.render_data_table(vouchers);

		let transaction_amount = this.transaction.withdrawal || this.transaction.deposit;
		this.render_transaction_amount_summary(
			flt(transaction_amount),
			flt(this.transaction.unallocated_amount),
			this.transaction.currency,
		);
	}

	update_filters_in_state(document_types) {
		Object.keys(this.panel_manager.actions_filters).map((key) => {
			let value = document_types.includes(key) ? 1 : 0;
			this.panel_manager.actions_filters[key] = value;
		})
	}

	render_data_table(vouchers) {
		this.summary_data = {};
		this.match_params = {};
		let table_data = vouchers.map((row) => {
			this.match_params[row.name] = {
				"Reference No": row.reference_number_match || 0,
				"Party": row.party_match || 0,
				"Transaction Amount": row.amount_match || 0,
				"Unallocated Amount": row.unallocated_amount_match || 0,
				"Name in Description": row.name_in_desc_match || 0,
			}
			return [
				this.help_button(row.name),
				row.doctype,
				row.reference_date || row.posting_date, // Reference Date
				format_currency(row.paid_amount, row.currency),
				row.reference_no || '',
				row.party || '',
				row.name
			];
		});

		const datatable_options = {
			columns: this.get_data_table_columns(),
			data: table_data,
			dynamicRowHeight: true,
			checkboxColumn: true,
			inlineFilters: true,
		};


		this.actions_table = new frappe.DataTable(
			this.match_field_group.get_field("vouchers").$wrapper[0],
			datatable_options
		);

		// Highlight first row
		this.actions_table.style.setStyle(
			".dt-cell[data-row-index='0']", {backgroundColor: '#F4FAEE'}
		);

		this.bind_row_check_event();
		this.bind_help_button();
	}

	help_button(voucher_name) {
		return `
			<div class="w-100" style="text-align: center;">
				<button class="btn btn-default btn-xs match-reasons-btn" data-name=${voucher_name}>
					<svg class="icon icon-sm">
						<use href="#icon-help"></use>
					</svg>
				</button>
			</div>
		`;
	}

	bind_row_check_event() {
		// Resistant to row removal on being out of view in datatable
		$(this.actions_table.bodyScrollable).on("click", ".dt-cell__content input", (e) => {
			let idx = $(e.currentTarget).closest(".dt-cell").data().rowIndex;
			let voucher_row = this.actions_table.getRows()[idx];

			this.check_data_table_row(voucher_row)
		})
	}

	bind_help_button() {
		var me = this;
		$(this.actions_table.bodyScrollable).on("mouseenter", ".match-reasons-btn", (e) => {
			let $btn = $(e.currentTarget);
			let voucher_name = $btn.data().name;
			$btn.popover({
				trigger: "manual",
				placement: "top",
				html: true,
				content: () => {
					return `
						<div>
							<div class="match-popover-header">${__("Match Reasons")}</div>
							${me.get_match_reasons(voucher_name)}
						</div>
					`;

				}
			});
			$btn.popover("toggle");
		});

		$(this.actions_table.bodyScrollable).on("mouseleave", ".match-reasons-btn", (e) => {
			let $btn = $(e.currentTarget);
			$btn.popover("toggle");
		});
	}

	get_match_reasons(voucher_name) {
		let reasons = this.match_params[voucher_name], html = "";
		for (let key in reasons) {
			if (reasons[key]) {
				html += `<div class="muted">${__(key)}</div>`;
			}
		}
		return html || __("No Specific Match Reasons");

	}

	check_data_table_row(row) {
		if (!row) return;

		let id = row[1].content;
		let value = this.get_amount_from_row(row);

		// If `id` in summary_data, remove it (row was unchecked), else add it
		if (id in this.summary_data) {
			delete this.summary_data[id];
		} else {
			this.summary_data[id] = value;
		}

		// Total of selected row amounts in summary_data
		let total_allocated = Object.values(this.summary_data).reduce(
			(a, b) => a + b, 0
		);

		// Deduct allocated amount from transaction's unallocated amount
		// to show the final effect on reconciling
		let transaction_amount = this.transaction.withdrawal || this.transaction.deposit;
		let unallocated = flt(this.transaction.unallocated_amount) - flt(total_allocated);

		this.render_transaction_amount_summary(
			flt(transaction_amount), unallocated, this.transaction.currency,
		);
	}

	render_transaction_amount_summary(total_amount, unallocated_amount, currency) {
		let summary_field = this.match_field_group.get_field("transaction_amount_summary").$wrapper;
		summary_field.empty();

		let allocated_amount = flt(total_amount) - flt(unallocated_amount);

		new erpnext.accounts.bank_reconciliation.SummaryCard({
			$wrapper: summary_field,
			values: {
				"Amount": [total_amount],
				"Allocated Amount": [allocated_amount],
				"To Allocate": [
					unallocated_amount,
					(unallocated_amount < 0 ? "text-danger" : unallocated_amount > 0 ? "text-blue" : "text-success")
				]
			},
			currency: currency,
			wrapper_class: "reconciliation-summary"
		});
	}

	async get_matching_vouchers(document_types) {
		let vouchers = await frappe.call({
			method:
				"erpnext.accounts.doctype.bank_reconciliation_tool_beta.bank_reconciliation_tool_beta.get_linked_payments",
			args: {
				bank_transaction_name: this.transaction.name,
				document_types: document_types,
				from_date: this.doc.bank_statement_from_date,
				to_date: this.doc.bank_statement_to_date,
				filter_by_reference_date: this.doc.filter_by_reference_date,
				from_reference_date: this.doc.from_reference_date,
				to_reference_date: this.doc.to_reference_date
			},
		}).then(result => result.message);
		return vouchers || [];
	}

	update_bank_transaction() {
		var me = this;
		const reference_number = this.details_field_group.get_value("reference_number");
		const party = this.details_field_group.get_value("party");
		const party_type = this.details_field_group.get_value("party_type");

		let diff = ["reference_number", "party", "party_type"].some(field => {
			return me.details_field_group.get_value(field) !== me.transaction[field];
		});
		if (!diff) {
			frappe.show_alert({message: __("No changes to update"), indicator: "yellow"});
			return;
		}

		frappe.call({
			method:
				"erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.update_bank_transaction",
			args: {
				bank_transaction_name: me.transaction.name,
				reference_number: reference_number,
				party_type: party_type,
				party: party,
			},
			freeze: true,
			freeze_message: __("Updating ..."),
			callback: (response) => {
				if (response.exc) {
					frappe.show_alert(__("Failed to update {0}", [me.transaction.name]));
					return;
				}

				// Update transaction
				me.panel_manager.refresh_transaction(
					null, reference_number, party_type, party
				);

				frappe.show_alert(
					__("Bank Transaction {0} updated", [me.transaction.name])
				);
			},
		});
	}

	reconcile_selected_vouchers() {
		var me = this;
		let selected_vouchers = [];
		let selected_map = this.actions_table.rowmanager.checkMap;
		let voucher_rows = this.actions_table.getRows();

		selected_map.forEach((value, idx) => {
			if (value === 1) {
				let row = voucher_rows[idx];
				selected_vouchers.push({
					payment_doctype: row[3].content,
					payment_name: row[8].content,
					amount: this.get_amount_from_row(row),
				});
			}
		});

		if (!selected_vouchers.length > 0) {
			frappe.show_alert({
				message: __("Please select at least one voucher to reconcile"),
				indicator: "red"
			});
			return;
		}

		frappe.call({
			method:
				"erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.reconcile_vouchers",
			args: {
				bank_transaction_name: this.transaction.name,
				vouchers: selected_vouchers,
			},
			freeze: true,
			freeze_message: __("Reconciling ..."),
			callback: (response) => {
				if (response.exc) {
					frappe.show_alert({
						message: __("Failed to reconcile {0}", [this.transaction.name]),
						indicator: "red"
					});
					return;
				}

				me.after_transaction_reconcile(response.message, false);
			},
		});
	}

	create_voucher() {
		var me = this;
		let values = this.create_field_group.get_values();
		let document_type = values.document_type;

		// Create new voucher and delete or refresh current BT row depending on reconciliation
		this.create_voucher_bts(
			null,
			(message) => me.after_transaction_reconcile(message, true, document_type)
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

	after_transaction_reconcile(message, with_new_voucher=false, document_type) {
		// Actions after a transaction is matched with a voucher
		// `with_new_voucher`: If a new voucher was created and reconciled with the transaction
		let doc = message;
		let unallocated_amount = flt(doc.unallocated_amount);
		if (unallocated_amount > 0) {
			// if partial update this.transaction, re-click on list row
			frappe.show_alert({
				message: __(
					"Bank Transaction {0} Partially {1}",
					[this.transaction.name, with_new_voucher ? "Reconciled" : "Matched"]
				),
				indicator: "blue"
			});
			this.panel_manager.refresh_transaction(unallocated_amount);
		} else {
			let alert_string = __("Bank Transaction {0} Matched", [this.transaction.name])
			if (with_new_voucher) {
				alert_string = __("Bank Transaction {0} reconciled with a new {1}", [this.transaction.name, document_type]);
			}
			frappe.show_alert({message: alert_string, indicator: "green"});
			this.panel_manager.move_to_next_transaction();
		}
	}

	get_amount_from_row(row) {
		let value = row[5].content;
		return flt(value.split(" ") ? value.split(" ")[1] : 0);
	}

	get_match_tab_fields() {
		const filters_state = this.panel_manager.actions_filters;
		return [
			{
				label: __("Payment Entry"),
				fieldname: "payment_entry",
				fieldtype: "Check",
				default: filters_state.payment_entry,
				onchange: () => {
					this.populate_matching_vouchers();
				}
			},
			{
				label: __("Journal Entry"),
				fieldname: "journal_entry",
				fieldtype: "Check",
				default: filters_state.journal_entry,
				onchange: () => {
					this.populate_matching_vouchers();
				}
			},
			{
				fieldtype: "Column Break"
			},
			{
				label: __("Purchase Invoice"),
				fieldname: "purchase_invoice",
				fieldtype: "Check",
				default: filters_state.purchase_invoice,
				onchange: () => {
					let value = this.match_field_group.get_value("purchase_invoice");
					this.match_field_group.get_field("unpaid_invoices").df.hidden = !value;
					this.match_field_group.refresh();

					this.populate_matching_vouchers();
				}
			},
			{
				label: __("Sales Invoice"),
				fieldname: "sales_invoice",
				fieldtype: "Check",
				default: filters_state.sales_invoice,
				onchange: () => {
					let value = this.match_field_group.get_value("sales_invoice");
					this.match_field_group.get_field("unpaid_invoices").df.hidden = !value;
					this.match_field_group.refresh();

					this.populate_matching_vouchers();
				}
			},
			{
				fieldtype: "Column Break"
			},
			{
				label: __("Loan Repayment"),
				fieldname: "loan_repayment",
				fieldtype: "Check",
				default: filters_state.loan_repayment,
				onchange: () => {
					this.populate_matching_vouchers();
				}
			},
			{
				label: __("Loan Disbursement"),
				fieldname: "loan_disbursement",
				fieldtype: "Check",
				default: filters_state.loan_disbursement,
				onchange: () => {
					this.populate_matching_vouchers();
				}
			},
			{
				fieldtype: "Column Break"
			},
			{
				label: __("Expense Claim"),
				fieldname: "expense_claim",
				fieldtype: "Check",
				default: filters_state.expense_claim,
				onchange: () => {
					this.populate_matching_vouchers();
				}
			},
			{
				label: __("Bank Transaction"),
				fieldname: "bank_transaction",
				fieldtype: "Check",
				default: filters_state.bank_transaction,
				onchange: () => {
					this.populate_matching_vouchers();
				}
			},
			{
				fieldtype: "Section Break"
			},
			{
				label: __("Show Exact Amount"),
				fieldname: "exact_match",
				fieldtype: "Check",
				default: filters_state.exact_match,
				onchange: () => {
					this.populate_matching_vouchers();
				}
			},
			{
				fieldtype: "Column Break"
			},
			{
				label: __("Show Exact Party"),
				fieldname: "exact_party_match",
				fieldtype: "Check",
				default: filters_state.exact_party_match,
				onchange: () => {
					this.populate_matching_vouchers();
				},
				read_only: !Boolean(this.transaction.party_type && this.transaction.party)
			},
			{
				fieldtype: "Column Break"
			},
			{
				label: __("Unpaid Invoices"),
				fieldname: "unpaid_invoices",
				fieldtype: "Check",
				default: filters_state.unpaid_invoices,
				onchange: () => {
					this.populate_matching_vouchers();
				},
				hidden: (filters_state.sales_invoice || filters_state.purchase_invoice) ? 0 : 1
			},
			{
				fieldtype: "Column Break"
			},
			{
				fieldtype: "Section Break"
			},
			{
				fieldname: "transaction_amount_summary",
				fieldtype: "HTML",
			},
			{
				fieldname: "vouchers",
				fieldtype: "HTML",
			},
			{
				fieldtype: "Section Break",
				fieldname: "section_break_reconcile",
				hide_border: 1,
			},
			{
				label: __("Hidden field for alignment"),
				fieldname: "hidden_field_2",
				fieldtype: "Data",
				hidden: 1
			},
			{
				fieldtype: "Column Break"
			},
			{
				label: __("Reconcile"),
				fieldname: "bt_reconcile",
				fieldtype: "Button",
				primary: true,
				click: () => {
					this.reconcile_selected_vouchers();
				}
			}
		];
	}

	get_detail_tab_fields() {
		return  [
			{
				label: __("ID"),
				fieldname: "name",
				fieldtype: "Link",
				options: "Bank Transaction",
				default: this.transaction.name,
				read_only: 1,
			},
			{
				label: __("Date"),
				fieldname: "date",
				fieldtype: "Date",
				default: this.transaction.date,
				read_only: 1,
			},
			{
				label: __("Deposit"),
				fieldname: "deposit",
				fieldtype: "Currency",
				default: this.transaction.deposit,
				read_only: 1,
			},
			{
				label: __("Withdrawal"),
				fieldname: "withdrawal",
				fieldtype: "Currency",
				default: this.transaction.withdrawal,
				read_only: 1,
			},
			{
				fieldtype: "Column Break"
			},
			{
				label: __("Description"),
				fieldname: "description",
				fieldtype: "Small Text",
				default: this.transaction.description,
				read_only: 1,
			},
			{
				label: __("To Allocate"),
				fieldname: "unallocated_amount",
				fieldtype: "Currency",
				options: "account_currency",
				default: this.transaction.unallocated_amount,
				read_only: 1,
			},
			{
				label: __("Currency"),
				fieldname: "account_currency",
				fieldtype: "Link",
				options: "Currency",
				read_only: 1,
				default: this.transaction.currency,
				hidden: 1,
			},
			{
				label: __("Account Holder"),
				fieldname: "account",
				fieldtype: "Data",
				default: this.transaction.bank_party_name,
				read_only: 1,
				hidden: this.transaction.bank_party_name ? 0 : 1,
			},
			{
				label: __("Party Account Number"),
				fieldname: "account_number",
				fieldtype: "Data",
				default: this.transaction.bank_party_account_number,
				read_only: 1,
				hidden: this.transaction.bank_party_account_number ? 0 : 1,
			},
			{
				label: __("Party IBAN"),
				fieldname: "iban",
				fieldtype: "Data",
				default: this.transaction.bank_party_iban,
				read_only: 1,
				hidden: this.transaction.bank_party_iban ? 0 : 1,
			},
			{
				label: __("Update"),
				fieldtype: "Section Break",
				fieldname: "update_section",
			},
			{
				label: __("Reference Number"),
				fieldname: "reference_number",
				fieldtype: "Data",
				default: this.transaction.reference_number,
			},
			{
				fieldtype: "Column Break"
			},
			{
				label: __("Party Type"),
				fieldname: "party_type",
				fieldtype: "Link",
				options: "DocType",
				get_query: function () {
					return {
						filters: {
							name: [
								"in", Object.keys(frappe.boot.party_account_types),
							],
						},
					};
				},
				onchange: () => {
					let value = this.details_field_group.get_value("party_type");
					this.details_field_group.get_field("party").df.options = value;
				},
				default: this.transaction.party_type || null,
			},
			{
				label: __("Party"),
				fieldname: "party",
				fieldtype: "Link",
				default: this.transaction.party,
				options: this.transaction.party_type || null,
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
				label: __("Submit"),
				fieldname: "submit_transaction",
				fieldtype: "Button",
				primary: true,
				click: () => this.update_bank_transaction(),
			}
		];
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

					fields.get_field("project").df.hidden = value === "Journal Entry";
					fields.get_field("cost_center").df.hidden = value === "Journal Entry";

					fields.get_field("journal_entry_type").df.hidden = value === "Payment Entry";
					fields.get_field("journal_entry_type").df.reqd = value === "Journal Entry";
					fields.get_field("second_account").df.hidden = value === "Payment Entry";
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
				default: this.transaction.reference_number || this.transaction.description,
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
				hidden: 1,
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
							company: this.doc.company,
						},
					};
				},
				hidden: 1,
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
			},
			{
				fieldname: "cost_center",
				fieldtype: "Link",
				label: "Cost Center",
				options: "Cost Center",
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

	get_data_table_columns() {
		return [
			{
				name: __("Reason"),
				editable: false,
				width: 50,
			},
			{
				name: __("Document Type"),
				editable: false,
				width: 100,
			},
			{
				name: __("Reference Date"),
				editable: false,
				width: 120,
			},
			{
				name: __("Remaining"),
				editable: false,
				width: 100,
			},
			{
				name: __("Reference Number"),
				editable: false,
				width: 200,
			},
			{
				name: __("Party"),
				editable: false,
				width: 100,
			},
			{
				name: __("Document Name"),
				editable: false,
				width: 100,
			},
		];
	}
}