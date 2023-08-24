frappe.provide("erpnext.accounts.bank_reconciliation");

erpnext.accounts.bank_reconciliation.PanelManager = class PanelManager {
	constructor(opts) {
		Object.assign(this, opts);
		this.make();
	}

	make() {
		this.init_panels();
	}

	async init_panels() {
		this.transactions = await this.get_bank_transactions();

		this.$wrapper.empty();
		this.$panel_wrapper = this.$wrapper.append(`
			<div class="panel-container d-flex"></div>
		`).find(".panel-container");

		this.render_panels()
	}

	async get_bank_transactions() {
		let transactions = await frappe.call({
			method:
				"erpnext.accounts.doctype.bank_reconciliation_tool_beta.bank_reconciliation_tool_beta.get_bank_transactions",
			args: {
				bank_account: this.doc.bank_account,
				from_date: this.doc.bank_statement_from_date,
				to_date: this.doc.bank_statement_to_date,
				order_by: this.order || "date asc",
			},
			freeze: true,
			freeze_message: __("Fetching Bank Transactions"),
		}).then(response => response.message);
		return transactions;
	}

	render_panels() {
		this.set_actions_panel_default_states();

		if (!this.transactions || !this.transactions.length) {
			this.render_no_transactions();
		} else {
			this.render_list_panel();

			let first_transaction = this.transactions[0];
			this.$list_container.find("#" + first_transaction.name).click();
		}
	}

	set_actions_panel_default_states() {
		// Init actions panel states to store for persistent views
		this.actions_tab = "match_voucher-tab";
		this.actions_filters = {
			payment_entry: 1,
			journal_entry: 1,
			purchase_invoice: 0,
			sales_invoice: 0,
			loan_repayment: 0,
			loan_disbursement: 0,
			expense_claim: 0,
			bank_transaction: 0,
			exact_match: 0,
			exact_party_match: 0,
			unpaid_invoices: 0
		}
	}

	render_no_transactions() {
		this.$panel_wrapper.empty();
		this.$panel_wrapper.append(`
			<div class="no-transactions">
				<img src="/assets/frappe/images/ui-states/list-empty-state.svg" alt="Empty State">
				<p>${__("No Transactions found for the current filters.")}</p>
			</div>
		`);
	}

	render_list_panel() {
		this.$panel_wrapper.append(`
			<div class="list-panel">
				<div class="sort-by"></div>
				<div class="list-container"></div>
			</div>
		`);

		this.render_sort_area();
		this.render_transactions_list();
	}

	render_actions_panel() {
		this.actions_panel =  new erpnext.accounts.bank_reconciliation.ActionsPanel({
			$wrapper: this.$panel_wrapper,
			transaction: this.active_transaction,
			doc: this.doc,
			panel_manager: this
		});
	}

	render_sort_area() {
		this.$sort_area = this.$panel_wrapper.find(".sort-by");
		this.$sort_area.append(`
			<div class="sort-by-title"> ${__("Sort By")} </div>
			<div class="sort-by-selector p-10"></div>
		`);

		var me = this;
		new frappe.ui.SortSelector({
			parent: me.$sort_area.find(".sort-by-selector"),
			args: {
				sort_by: me.order_by || "date",
				sort_order: me.order_direction || "asc",
				options: [
					{fieldname: "date", label: __("Date")},
					{fieldname: "withdrawal", label: __("Withdrawal")},
					{fieldname: "deposit", label: __("Deposit")},
					{fieldname: "unallocated_amount", label: __("Unallocated Amount")}
				]
			},
			change: function(sort_by, sort_order) {
				// Globally set the order used in the re-rendering of the list
				me.order_by = (sort_by || me.order_by || "date");
				me.order_direction = (sort_order || me.order_direction || "asc");
				me.order =  me.order_by + " " + me.order_direction;

				// Re-render the list
				me.init_panels();
			}
		});
	}

	render_transactions_list() {
		this.$list_container = this.$panel_wrapper.find(".list-container");

		this.transactions.map(transaction => {
			let amount = transaction.deposit || transaction.withdrawal;
			let symbol = transaction.withdrawal ? "-" : "+";

			let $row = this.$list_container.append(`
				<div id="${transaction.name}" class="transaction-row p-10">
					<!-- Date & Amount -->
					<div class="d-flex">
						<div class="w-50">
							<span title="${__("Date")}">${frappe.format(transaction.date, {fieldtype: "Date"})}</span>
						</div>

						<div class="w-50 bt-amount-contianer">
							<span
								title="${__("Amount")}"
								class="bt-amount ${transaction.withdrawal ? 'text-danger' : 'text-success'}"
							>
								<b>${symbol} ${format_currency(amount, transaction.currency)}</b>
							</span>
						</div>
					</div>


					<!-- Description, Reference, Party -->
					<div
						title="${__("Account Holder")}"
						class="account-holder ${transaction.bank_party_name ? '' : 'hide'}"
					>
						<span class="account-holder-value">${transaction.bank_party_name}</span>
					</div>

					<div
						title="${__("Description")}"
						class="description ${transaction.description ? '' : 'hide'}"
					>
						<span class="description-value">${transaction.description}</span>
					</div>

					<div
						title="${__("Reference")}"
						class="reference ${transaction.reference_number ? '' : 'hide'}"
					>
						<span class="reference-value">${transaction.reference_number}</span>
					</div>
				</div>
			`).find("#" + transaction.name);

			$row.on("click", () => {
				$row.addClass("active").siblings().removeClass("active");

				// this.transaction's objects get updated, we want the latest values
				this.active_transaction = this.transactions.find(({name}) => name === transaction.name);
				this.render_actions_panel();
			})
		})
	}

	refresh_transaction(updated_amount=null, reference_number=null, party_type=null, party=null) {
		// Update the transaction object's unallocated_amount **OR** other details
		let id = this.active_transaction.name;
		let current_index = this.transactions.findIndex(({name}) => name === id);

		let $current_transaction = this.$list_container.find("#" + id);
		let transaction = this.transactions[current_index];

		if (updated_amount) {
			// update amount is > 0 always [src: `after_transaction_reconcile()`]
			this.transactions[current_index]["unallocated_amount"] = updated_amount;
		} else {
			this.transactions[current_index] = {
				...transaction,
				reference_number: reference_number,
				party_type: party_type,
				party: party
			};
			// Update Reference Number in List
			$current_transaction.find(".reference").removeClass("hide");
			$current_transaction.find(".reference-value").text(reference_number || "--");
		}

		$current_transaction.click();
	}

	move_to_next_transaction() {
		let id = this.active_transaction.name;
		let $current_transaction = this.$list_container.find("#" + id);
		let current_index = this.transactions.findIndex(({name}) => name === id);

		let next_transaction = this.transactions[current_index + 1];
		let previous_transaction = this.transactions[current_index - 1];

		if (next_transaction) {
			this.active_transaction = next_transaction;
			let $next_transaction = $current_transaction.next();
			$next_transaction.click();
		} else if (previous_transaction) {
			this.active_transaction = previous_transaction;
			let $previous_transaction = $current_transaction.prev();
			$previous_transaction.click();
		}

		this.transactions.splice(current_index, 1);
		$current_transaction.remove();

		if (!next_transaction && !previous_transaction) {
			this.active_transaction = null;
			this.render_no_transactions();
		}

	}
}