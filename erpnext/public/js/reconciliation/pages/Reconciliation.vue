<template>
	<div class="reconciliation-container">
		<bank-accounts-container
			:container_name="page_title"
			:accounts="accounts"
			:account_id_fieldname="account_id_fieldname"
			:on_click="select_account"
			:empty_state_message="empty_state_message"
			:selected_account="selected_account"
			:show_plaid_link="show_plaid_link"
			:plaid_env="plaid_env"
			:plaid_public_key="plaid_public_key"
			:client_name="client_name"
			:plaidSuccess="plaid_success"
			:plaid_subtitle="plaid_subtitle"
		>
		</bank-accounts-container>

		<div class="row">
			<div ref="from-date" class="col-xs-6"></div>
			<div ref="to-date" class="col-xs-6"></div>
		</div>
		<div v-show="mandatory_fields_completed" class="text-center">
			<button
				class="btn btn-primary"
				@click="sync_account">
				{{ __('Synchronize this account') }}
			</button>

			<button
				class="btn btn-primary"
				@click="get_transactions">
				{{ __('Get unreconciled transactions') }}
			</button>
		</div>

		<transactions-container
			:container_name="page_title"
			:transactions="transactions"
			:transaction_id_fieldname="transaction_id_fieldname"
			:on_click="select_transaction"
			:empty_state_message="empty_state_message"
			:selected_transaction="selected_transaction"
		>
		</transactions-container>
	</div>
</template>

<script>

import BankAccountsContainer from '../components/BankAccountsContainer.vue';
import TransactionsContainer from '../components/TransactionsContainer.vue';

export default {
	props: {
		company: String,
		accounts: Array,
		getBankAccounts: Function
	},
	components: {
		BankAccountsContainer,
		TransactionsContainer
	},
	data() {
		return {
			account_id_fieldname: 'name',
			page_title: __('Accounts'),
			empty_state_message: __(`Please select an account first.`),
			selected_account: {},
			bank_entries: {},
			transactions: [],
			transaction_id_fieldname: 'name',
			selected_transaction: {},
			client_name: "Test App",
			plaid_env : null,
			plaid_public_key: null,
			show_plaid_link: false,
			plaid_subtitle: __("Add a new account")
		}
	},
	created() {
		let me = this;
		frappe.xcall('erpnext.erpnext_integrations.doctype.plaid_settings.plaid_settings.plaid_configuration')
		.then(result => {
			me.plaid_env = result.plaid_env;
			me.plaid_public_key = result.plaid_public_key;
			me.client_name = result.client_name;
			me.show_plaid_link = true;
		})

		this.getBankAccounts();
	},
	mounted() {
	},
	computed: {
		mandatory_fields_completed() {
			if (this.selected_account.name !== undefined) {
				return true;
			} else {
				return false;
			}
		}
	},
	methods: {
		select_account(account) {
			if (this.selected_account == account) {
				this.selected_account = {}
			} else {
				this.selected_account = account
			}
		},

		get_transactions() {
			frappe.db.get_list('Bank Transaction', {
				fields: ['name', 'date', 'status', 'debit', 'credit', 'currency', 'description'],
				filters: {"docstatus": 1},
				or_filters: [['reference_number', '=', '']]

			}).then((transactions) => {
				this.transactions = transactions;
			})
		},

		plaid_success(token, response) {
			frappe.xcall('erpnext.erpnext_integrations.doctype.plaid_settings.plaid_settings.add_institution', {token: token, response: response})
			.then((result) => {
				frappe.xcall('erpnext.erpnext_integrations.doctype.plaid_settings.plaid_settings.add_bank_accounts', {response: response, bank: result})
			})
			.then((result) => {
				this.getBankAccounts();
			})
		},

		sync_account() {
			frappe.xcall('erpnext.erpnext_integrations.doctype.plaid_settings.plaid_settings.sync_transactions', {
				bank: this.selected_account.bank,
				bank_account: this.selected_account.name
			})
			.then((result) => {
				this.get_transactions();
			})
		},

		select_transaction() {

		}

	}
};
</script>
<style lang="less" scoped>
button {
	margin: 25px 25px;
}
</style>