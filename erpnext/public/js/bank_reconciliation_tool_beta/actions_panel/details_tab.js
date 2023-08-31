frappe.provide("erpnext.accounts.bank_reconciliation");

erpnext.accounts.bank_reconciliation.DetailsTab = class DetailsTab {
	constructor(opts) {
		$.extend(this, opts);
		this.make();
	}

	make() {
		this.panel_manager.actions_tab = "details-tab";

		this.details_field_group = new frappe.ui.FieldGroup({
			fields: this.get_detail_tab_fields(),
			body: this.actions_panel.$tab_content,
			card_layout: true,
		});
		this.details_field_group.make();
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
}