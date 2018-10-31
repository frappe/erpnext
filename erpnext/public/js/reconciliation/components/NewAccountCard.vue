<template>
	<div class="col-md-3 col-sm-4 col-xs-6 new-account-card-container">
		<div class="account-card text-center"
			@click="on_click()"
		>
			<div class="account-card-header flex justify-between">
				<div class="ellipsis">
					<div class="new-account-card-text ellipsis text-muted" v-html='subtitle'></div>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
export default {
	name: 'new-account-card',
	data() {
		return {
			subtitle: __("Add a new account")
		}
	},
	methods: {
		on_click() {
			frappe.new_doc("Bank Account")
		}
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
		border-style: dashed;
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