<template>
	<div class="bank-accounts-container">
		<account-card
			v-for="account in accounts"
			:key="container_name + '_' +account[account_id_fieldname]"
			:account="account"
			:on_click="on_click"
			:account_id_fieldname="account_id_fieldname"
			:selected_account="selected_account"
		>
		</account-card>
		<new-account-card
			v-if="accounts.length > 0 && !show_plaid_link"
		>
		</new-account-card>
		<PlaidLink
			v-if="show_plaid_link"
			:env="plaid_env"
			:publicKey="plaid_public_key"
			:clientName="client_name"
			:product='["transactions", "auth"]'
			v-bind="{ plaidSuccess }"
			:subtitle="plaid_subtitle">
		</PlaidLink>
	</div>
</template>

<script>

import AccountCard from './AccountCard.vue';
import NewAccountCard from './NewAccountCard.vue';
import PlaidLink from '../components/PlaidLink.vue'

export default {
	name: 'account-cards-container',
	props: {
		container_name: String,
		accounts: Array,
		account_id_fieldname: String,
		is_local: Boolean,
		on_click: Function,
		editable: Boolean,
		selected_account: Object,
		show_plaid_link: Boolean,
		plaid_env: String,
		plaid_public_key: String,
		client_name: String,
		plaidSuccess: Function,
		plaid_subtitle: String

	},
	components: {
		AccountCard,
		NewAccountCard,
		PlaidLink
	},
	data() {
		return {
			section_title: __("Please select a bank account"),
			onSuccess: this.plaid_on_success
		}
	}
}
</script>

<style scoped>
	.bank-accounts-container {
		margin: 0 -15px;
		overflow: overlay;
	}
</style>