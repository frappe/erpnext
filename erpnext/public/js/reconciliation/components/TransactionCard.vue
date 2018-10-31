<template>
	<tr class="transaction-card text-center"
		@click="on_click(transaction)"
	>
		<td>{{ transaction.description }}</td>
		<td>{{ amount }}</td>
		<td>{{ transaction.currency }}</td>
		<td>{{ date }}</td>
	</tr>
</template>

<script>
export default {
	name: 'transaction-card',
	props: ['transaction', 'transaction_id_fieldname', 'on_click', 'selected_transaction'],
	computed: {
		amount() {
			const amount = (parseFloat(this.transaction.credit) > 0) ? -Math.abs(parseFloat(this.transaction.credit)) : parseFloat(this.transaction.debit);
			return amount;
		},
		date() {
			const date = moment(this.transaction.date)
			return frappe.datetime.obj_to_user(date);
		}
	}
}
</script>

<style lang="less" scoped>
	@import "../../../../../../frappe/frappe/public/less/variables.less";
	.transaction-card {
		height: 60px;
		cursor: pointer;
	}

	table {
		td {
			text-align: left;
		}
	}
</style>