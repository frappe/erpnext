<template>
	<div class="col-md-3 col-sm-4 col-xs-6 account-card-container">
		<div class="account-card text-center"
			@click="on_click(account)"
		>
			<div v-bind:class="getClass">
				<div class="ellipsis" :style="{ width: '85%' }">
					<div class="account-card-title ellipsis bold">{{ title }}</div>
					<div class="account-card-subtitle ellipsis text-muted" v-html='subtitle'></div>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
export default {
	name: 'account-card',
	props: ['account', 'account_id_fieldname', 'on_click', 'selected_account'],
	computed: {
		title() {
			const account_name = this.account.name;
			return account_name;
		},
		subtitle() {
			return "Test"
		},
		getClass() {
			let value = (this.account.name == this.selected_account.name) ? "account-card-header flex justify-between selected" : "account-card-header flex justify-between"
			return value;
		}
	},
	method: {
		
	}
}
</script>

<style lang="less" scoped>
	@import "../../../../../../frappe/frappe/public/less/variables.less";
	.account-card {
		margin-bottom: 25px;
		position: relative;
		border: 1px solid @border-color;
		border-radius: 4px;
		overflow: hidden;
		cursor: pointer;
		&:hover .account-card-overlay {
			display: block;
		}
	}
	.account-card-header {
		position: relative;
		padding: 12px 15px;
		height: 60px;
	}
	.account-card-body {
		position: relative;
		height: 200px;
	}
	.account-card-overlay {
		display: none;
		position: absolute;
		top: 0;
		width: 100%;
		height: 100%;
		background-color: rgba(0, 0, 0, 0.05);
	}
	.account-card-overlay-body {
		position: relative;
		height: 100%;
	}
	.account-card-overlay-button {
		position: absolute;
		right: 15px;
		bottom: 15px;
	}
</style>