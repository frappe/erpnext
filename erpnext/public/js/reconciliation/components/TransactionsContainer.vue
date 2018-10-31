<template>
	<div class="transactions-container">
		<empty-state
			v-if="transactions.length === 0"
			:message="empty_state_message"
			:action="empty_state_action"
			:bordered="false"
			:height="empty_state_height"
		/>
		<table class="table table-bordered table-hover" v-if="transactions.length > 0">
			<thead>
				<tr>
					<th>{{ __('Description') }}</th>
					<th>{{ __('Amount') }}</th>
					<th>{{ __('Currency') }}</th>
					<th>{{ __('Date') }}</th>
				</tr>
			</thead>
			<tbody>
				<transaction-card
					v-for="transaction in transactions"
					:key="container_name + '_' +transaction[transaction_id_fieldname]"
					:transaction="transaction"
					:on_click="on_click"
					:transaction_id_fieldname="transaction_id_fieldname"
					:selected_transaction="selected_transaction"
				>
				</transaction-card>
			</tbody>
		</table>
	</div>
</template>

<script>

import TransactionCard from './TransactionCard.vue';
import EmptyState from './EmptyState.vue';

export default {
	name: 'transactions-container',
	props: {
		container_name: String,
		transactions: Array,
		transaction_id_fieldname: String,
		is_local: Boolean,
		on_click: Function,
		editable: Boolean,
		empty_state_message: String,
		empty_state_action: Object,
		empty_state_height: Number,
		empty_state_bordered: Boolean,
		selected_transaction: Object
	},
	components: {
		TransactionCard,
		EmptyState
	}
}
</script>

<style scoped>
	.transactions-container {
		margin: 35px -15px;
		overflow: overlay;
	}

	table {
		tr {
			text-align: left;
		}
	}
</style>