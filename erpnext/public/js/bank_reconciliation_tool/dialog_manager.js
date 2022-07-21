frappe.provide("erpnext.accounts.bank_reconciliation");

erpnext.accounts.bank_reconciliation.DialogManager = class DialogManager {
	constructor(company, bank_account) {
		this.bank_account = bank_account;
		this.company = company;
		this.make_dialog();
	}

	show_dialog(bank_transaction_name, update_dt_cards) {
		this.bank_transaction_name = bank_transaction_name;
		this.update_dt_cards = update_dt_cards;
		frappe.call({
			method: "frappe.client.get_value",
			args: {
				doctype: "Bank Transaction",
				filters: { name: this.bank_transaction_name },
				fieldname: [
					"date as reference_date",
					"deposit",
					"withdrawal",
					"currency",
					"description",
					"name",
					"bank_account",
					"company",
					"reference_number",
					"party_type",
					"party",
					"unallocated_amount",
					"allocated_amount",
				],
			},
			callback: (r) => {
				if (r.message) {
					this.bank_transaction = r.message;
					r.message.payment_entry = 1;
					this.dialog.set_values(r.message);
					this.dialog.show();
				}
			},
		});
	}

	get_linked_vouchers(document_types) {
		frappe.call({
			method:
				"erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.get_linked_payments",
			args: {
				bank_transaction_name: this.bank_transaction_name,
				document_types: document_types,
			},

			callback: (result) => {
				const data = result.message;


				if (data && data.length > 0) {
					const proposals_wrapper = this.dialog.fields_dict.payment_proposals.$wrapper;
					proposals_wrapper.show();
					this.dialog.fields_dict.no_matching_vouchers.$wrapper.hide();
					this.data = [];
					data.forEach((row) => {
						const reference_date = row[5] ? row[5] : row[8];
						this.data.push([
							row[1],
							row[2],
							reference_date,
							format_currency(row[3], row[9]),
							row[6],
							row[4],
						]);
					});
					this.get_dt_columns();
					this.get_datatable(proposals_wrapper);
				} else {
					const proposals_wrapper = this.dialog.fields_dict.payment_proposals.$wrapper;
					proposals_wrapper.hide();
					this.dialog.fields_dict.no_matching_vouchers.$wrapper.show();

				}
				this.dialog.show();
			},
		});
	}

	get_dt_columns() {
		this.columns = [
			{
				name: "Document Type",
				editable: false,
				width: 125,
			},
			{
				name: "Document Name",
				editable: false,
				width: 150,
			},
			{
				name: "Reference Date",
				editable: false,
				width: 120,
			},
			{
				name: "Amount",
				editable: false,
				width: 100,
			},
			{
				name: "Party",
				editable: false,
				width: 120,
			},

			{
				name: "Reference Number",
				editable: false,
				width: 140,
			},
		];
	}

	get_datatable(proposals_wrapper) {
		if (!this.datatable) {
			const datatable_options = {
				columns: this.columns,
				data: this.data,
				dynamicRowHeight: true,
				checkboxColumn: true,
				inlineFilters: true,
			};
			this.datatable = new frappe.DataTable(
				proposals_wrapper.get(0),
				datatable_options
			);
		} else {
			this.datatable.refresh(this.data, this.columns);
			this.datatable.rowmanager.checkMap = [];
		}
	}

	make_dialog() {
		const me = this;
		me.selected_payment = null;

		const fields = [
			{
				label: __("Action"),
				fieldname: "action",
				fieldtype: "Select",
				options: `Match Against Voucher\nCreate Voucher\nUpdate Bank Transaction`,
				default: "Match Against Voucher",
			},
			{
				fieldname: "column_break_4",
				fieldtype: "Column Break",
			},
			{
				label: __("Document Type"),
				fieldname: "document_type",
				fieldtype: "Select",
				options: `Payment Entry\nJournal Entry`,
				default: "Payment Entry",
				depends_on: "eval:doc.action=='Create Voucher'",
			},
			{
				fieldtype: "Section Break",
				fieldname: "section_break_1",
				label: __("Filters"),
				depends_on: "eval:doc.action=='Match Against Voucher'",
			},
		];

		frappe.call({
			method: "erpnext.accounts.doctype.bank_transaction.bank_transaction.get_doctypes_for_bank_reconciliation",
			callback: (r) => {
				$.each(r.message, (_i, entry) => {
					if (_i % 3 == 0) {
						fields.push({
							fieldtype: "Column Break",
						});
					}
					fields.push({
						fieldtype: "Check",
						label: entry,
						fieldname: frappe.scrub(entry),
						onchange: () => this.update_options(),
					});
				});

				fields.push(...this.get_voucher_fields());

				me.dialog = new frappe.ui.Dialog({
					title: __("Reconcile the Bank Transaction"),
					fields: fields,
					size: "large",
					primary_action: (values) =>
						this.reconciliation_dialog_primary_action(values),
				});
			}
		});
	}

	get_voucher_fields() {
		return [
			{
				fieldtype: "Check",
				label: "Show Only Exact Amount",
				fieldname: "exact_match",
				onchange: () => this.update_options(),
			},
			{
				fieldtype: "Section Break",
				fieldname: "section_break_1",
				label: __("Select Vouchers to Match"),
				depends_on: "eval:doc.action=='Match Against Voucher'",
			},
			{
				fieldtype: "HTML",
				fieldname: "payment_proposals",
			},
			{
				fieldtype: "HTML",
				fieldname: "no_matching_vouchers",
				options: "<div class=\"text-muted text-center\">No Matching Vouchers Found</div>"
			},
			{
				fieldtype: "Section Break",
				fieldname: "details",
				label: "Details",
				depends_on: "eval:doc.action!='Match Against Voucher'",
			},
			{
				fieldname: "reference_number",
				fieldtype: "Data",
				label: "Reference Number",
				mandatory_depends_on: "eval:doc.action=='Create Voucher'",
			},
			{
				default: "Today",
				fieldname: "posting_date",
				fieldtype: "Date",
				label: "Posting Date",
				reqd: 1,
				depends_on: "eval:doc.action=='Create Voucher'",
			},
			{
				fieldname: "reference_date",
				fieldtype: "Date",
				label: "Cheque/Reference Date",
				mandatory_depends_on: "eval:doc.action=='Create Voucher'",
				depends_on: "eval:doc.action=='Create Voucher'",
				reqd: 1,
			},
			{
				fieldname: "mode_of_payment",
				fieldtype: "Link",
				label: "Mode of Payment",
				options: "Mode of Payment",
				depends_on: "eval:doc.action=='Create Voucher'",
			},
			{
				fieldname: "edit_in_full_page",
				fieldtype: "Button",
				label: "Edit in Full Page",
				click: () => {
					this.edit_in_full_page();
				},
				depends_on:
					"eval:doc.action=='Create Voucher'",
			},
			{
				fieldname: "column_break_7",
				fieldtype: "Column Break",
			},
			{
				default: "Journal Entry Type",
				fieldname: "journal_entry_type",
				fieldtype: "Select",
				label: "Journal Entry Type",
				options:
					"Journal Entry\nInter Company Journal Entry\nBank Entry\nCash Entry\nCredit Card Entry\nDebit Note\nCredit Note\nContra Entry\nExcise Entry\nWrite Off Entry\nOpening Entry\nDepreciation Entry\nExchange Rate Revaluation\nDeferred Revenue\nDeferred Expense",
				depends_on:
					"eval:doc.action=='Create Voucher' &&  doc.document_type=='Journal Entry'",
				mandatory_depends_on:
					"eval:doc.action=='Create Voucher' &&  doc.document_type=='Journal Entry'",
			},
			{
				fieldname: "second_account",
				fieldtype: "Link",
				label: "Account",
				options: "Account",
				depends_on:
					"eval:doc.action=='Create Voucher' &&  doc.document_type=='Journal Entry'",
				mandatory_depends_on:
					"eval:doc.action=='Create Voucher' &&  doc.document_type=='Journal Entry'",
				get_query: () => {
					return {
						filters: {
							is_group: 0,
							company: this.company,
						},
					};
				},
			},
			{
				fieldname: "party_type",
				fieldtype: "Link",
				label: "Party Type",
				options: "DocType",
				mandatory_depends_on:
				"eval:doc.action=='Create Voucher' &&  doc.document_type=='Payment Entry'",
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
			},
			{
				fieldname: "party",
				fieldtype: "Dynamic Link",
				label: "Party",
				options: "party_type",
				mandatory_depends_on:
					"eval:doc.action=='Create Voucher' && doc.document_type=='Payment Entry'",
			},
			{
				fieldname: "project",
				fieldtype: "Link",
				label: "Project",
				options: "Project",
				depends_on:
					"eval:doc.action=='Create Voucher' && doc.document_type=='Payment Entry'",
			},
			{
				fieldname: "cost_center",
				fieldtype: "Link",
				label: "Cost Center",
				options: "Cost Center",
				depends_on:
					"eval:doc.action=='Create Voucher' && doc.document_type=='Payment Entry'",
			},
			{
				fieldtype: "Section Break",
				fieldname: "details_section",
				label: "Transaction Details",
				collapsible: 1,
			},
			{
				fieldname: "deposit",
				fieldtype: "Currency",
				label: "Deposit",
				read_only: 1,
			},
			{
				fieldname: "withdrawal",
				fieldtype: "Currency",
				label: "Withdrawal",
				read_only: 1,
			},
			{
				fieldname: "description",
				fieldtype: "Small Text",
				label: "Description",
				read_only: 1,
			},
			{
				fieldname: "column_break_17",
				fieldtype: "Column Break",
				read_only: 1,
			},
			{
				fieldname: "allocated_amount",
				fieldtype: "Currency",
				label: "Allocated Amount",
				read_only: 1,
			},

			{
				fieldname: "unallocated_amount",
				fieldtype: "Currency",
				label: "Unallocated Amount",
				read_only: 1,
			},
		];
	}

	get_selected_attributes() {
		let selected_attributes = [];
		this.dialog.$wrapper.find(".checkbox input").each((i, col) => {
			if ($(col).is(":checked")) {
				selected_attributes.push($(col).attr("data-fieldname"));
			}
		});

		return selected_attributes;
	}

	update_options() {
		let selected_attributes = this.get_selected_attributes();
		this.get_linked_vouchers(selected_attributes);
	}

	reconciliation_dialog_primary_action(values) {
		if (values.action == "Match Against Voucher") this.match(values);
		if (
			values.action == "Create Voucher" &&
			values.document_type == "Payment Entry"
		)
			this.add_payment_entry(values);
		if (
			values.action == "Create Voucher" &&
			values.document_type == "Journal Entry"
		)
			this.add_journal_entry(values);
		else if (values.action == "Update Bank Transaction")
			this.update_transaction(values);
	}

	match() {
		var selected_map = this.datatable.rowmanager.checkMap;
		let rows = [];
		selected_map.forEach((val, index) => {
			if (val == 1) rows.push(this.datatable.datamanager.rows[index]);
		});
		let vouchers = [];
		rows.forEach((x) => {
			vouchers.push({
				payment_doctype: x[2].content,
				payment_name: x[3].content,
				amount: x[5].content,
			});
		});
		frappe.call({
			method:
				"erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.reconcile_vouchers",
			args: {
				bank_transaction_name: this.bank_transaction.name,
				vouchers: vouchers,
			},
			callback: (response) => {
				const alert_string =
					"Bank Transaction " +
					this.bank_transaction.name +
					" Matched";
				frappe.show_alert(alert_string);
				this.update_dt_cards(response.message);
				this.dialog.hide();
			},
		});
	}

	add_payment_entry(values) {
		frappe.call({
			method:
				"erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.create_payment_entry_bts",
			args: {
				bank_transaction_name: this.bank_transaction.name,
				reference_number: values.reference_number,
				reference_date: values.reference_date,
				party_type: values.party_type,
				party: values.party,
				posting_date: values.posting_date,
				mode_of_payment: values.mode_of_payment,
				project: values.project,
				cost_center: values.cost_center,
			},
			callback: (response) => {
				const alert_string =
					"Bank Transaction " +
					this.bank_transaction.name +
					" added as Payment Entry";
				frappe.show_alert(alert_string);
				this.update_dt_cards(response.message);
				this.dialog.hide();
			},
		});
	}

	add_journal_entry(values) {
		frappe.call({
			method:
				"erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.create_journal_entry_bts",
			args: {
				bank_transaction_name: this.bank_transaction.name,
				reference_number: values.reference_number,
				reference_date: values.reference_date,
				party_type: values.party_type,
				party: values.party,
				posting_date: values.posting_date,
				mode_of_payment: values.mode_of_payment,
				entry_type: values.journal_entry_type,
				second_account: values.second_account,
			},
			callback: (response) => {
				const alert_string =
					"Bank Transaction " +
					this.bank_transaction.name +
					" added as Journal Entry";
				frappe.show_alert(alert_string);
				this.update_dt_cards(response.message);
				this.dialog.hide();
			},
		});
	}

	update_transaction(values) {
		frappe.call({
			method:
				"erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.update_bank_transaction",
			args: {
				bank_transaction_name: this.bank_transaction.name,
				reference_number: values.reference_number,
				party_type: values.party_type,
				party: values.party,
			},
			callback: (response) => {
				const alert_string =
					"Bank Transaction " +
					this.bank_transaction.name +
					" updated";
				frappe.show_alert(alert_string);
				this.update_dt_cards(response.message);
				this.dialog.hide();
			},
		});
	}

	edit_in_full_page() {
		const values = this.dialog.get_values(true);
		if (values.document_type == "Payment Entry") {
			frappe.call({
				method:
					"erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.create_payment_entry_bts",
				args: {
					bank_transaction_name: this.bank_transaction.name,
					reference_number: values.reference_number,
					reference_date: values.reference_date,
					party_type: values.party_type,
					party: values.party,
					posting_date: values.posting_date,
					mode_of_payment: values.mode_of_payment,
					project: values.project,
					cost_center: values.cost_center,
					allow_edit: true
				},
				callback: (r) => {
					const doc = frappe.model.sync(r.message);
					frappe.set_route("Form", doc[0].doctype, doc[0].name);
				},
			});
		} else {
			frappe.call({
				method:
					"erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.create_journal_entry_bts",
				args: {
					bank_transaction_name: this.bank_transaction.name,
					reference_number: values.reference_number,
					reference_date: values.reference_date,
					party_type: values.party_type,
					party: values.party,
					posting_date: values.posting_date,
					mode_of_payment: values.mode_of_payment,
					entry_type: values.journal_entry_type,
					second_account: values.second_account,
					allow_edit: true
				},
				callback: (r) => {
					var doc = frappe.model.sync(r.message);
					frappe.set_route("Form", doc[0].doctype, doc[0].name);
				},
			});
		}
	}

};
