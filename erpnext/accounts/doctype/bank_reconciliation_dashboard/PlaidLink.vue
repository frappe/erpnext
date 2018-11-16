<template>
	<div class="col-md-3 col-sm-4 col-xs-6 new-account-card-container">
		<div class="account-card text-center"
			@click="handleOnClick()"
		>
			<slot></slot>
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
	name: 'PlaidLink',
	props: {
		plaidUrl: {
			type: String,
			default: 'https://cdn.plaid.com/link/v2/stable/link-initialize.js'
		},
		env: {
			type: String,
			default: 'sandbox'
		},
		institution: String,
		selectAccount: Boolean,
		token: String,
		product: {
			type: Array,
			default: ["transactions"]
		},
		clientName: String,
		publicKey: String,
		webhook: String,
		plaidSuccess: Function,
		onExit: Function,
		onEvent: Function,
		subtitle: String
	},
	created () {
		this.loadScript(this.plaidUrl)
			.then(this.onScriptLoaded)
			.catch(this.onScriptError)
	},
	beforeDestroy () {
		if (window.linkHandler && window.linkHandler.open.lenth > 0) {
			window.linkHandler.exit()
		}
	},
	methods: {
		onScriptError (error) {
			console.error('There was an issue loading the link-initialize.js script')
		},
		onScriptLoaded () {
			window.linkHandler = window.Plaid.create({
				clientName: this.clientName,
				env: this.env,
				key: this.publicKey,
				onExit: this.onExit,
				onEvent: this.onEvent,
				onSuccess: this.plaidSuccess,
				product: this.product,
				selectAccount: this.selectAccount,
				token: this.token,
				webhook: this.webhook
			})
		},
		handleOnClick () {
			const institution = this.institution || null
			if (window.linkHandler) {
				window.linkHandler.open(institution)
			}
		},
		loadScript (src) {
			return new Promise(function (resolve, reject) {
				if (document.querySelector('script[src="' + src + '"]')) {
					resolve()
					return
				}
				const el = document.createElement('script')
				el.type = 'text/javascript'
				el.async = true
				el.src = src
				el.addEventListener('load', resolve)
				el.addEventListener('error', reject)
				el.addEventListener('abort', reject)
				document.head.appendChild(el)
			})
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