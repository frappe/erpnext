frappe.provide("erpnext.accounts.bank_reconciliation");

erpnext.accounts.bank_reconciliation.ActionsPanelManager = class ActionsPanelManager {
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
				this.$tab_content.empty();

				if (tab == "Details") {
					new erpnext.accounts.bank_reconciliation.DetailsTab({
						actions_panel: this,
						transaction: this.transaction,
						panel_manager: this.panel_manager,
					});
				} else if (tab == "Match Voucher") {
					new erpnext.accounts.bank_reconciliation.MatchTab({
						actions_panel: this,
						transaction: this.transaction,
						panel_manager: this.panel_manager,
						doc: this.doc,
					});
				} else {
					new erpnext.accounts.bank_reconciliation.CreateTab({
						actions_panel: this,
						transaction: this.transaction,
						panel_manager: this.panel_manager,
						company: this.doc.company,
					});
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
}