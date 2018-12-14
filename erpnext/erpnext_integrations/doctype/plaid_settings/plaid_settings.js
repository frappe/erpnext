// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.integrations")

frappe.ui.form.on('Plaid Settings', {
	link_new_account: function(frm) {
		new erpnext.integrations.plaidLink(frm)
	}
});

erpnext.integrations.plaidLink = class plaidLink {
	constructor(parent) {
		this.frm = parent;
		this.product = ["transactions", "auth"];
		this.plaidUrl = 'https://cdn.plaid.com/link/v2/stable/link-initialize.js';
		this.init_config();
	}

	init_config() {
		const me = this;
		frappe.xcall('erpnext.erpnext_integrations.doctype.plaid_settings.plaid_settings.plaid_configuration')
		.then(result => {
			if (result !== "disabled") {
				me.plaid_env = result.plaid_env;
				me.plaid_public_key = result.plaid_public_key;
				me.client_name = result.client_name;
				me.init_plaid()
			} else {
				frappe.throw(__("Please save your document before adding a new account"))
			}
		})
	}

	init_plaid() {
		const me = this;
		me.loadScript(me.plaidUrl)
			.then(() => {
				me.onScriptLoaded(me);
			})
			.then(() => {
				if (me.linkHandler) {
					me.linkHandler.open();
				}
			})
			.catch((error) => {
				me.onScriptError(error)
			})
	}

	loadScript(src) {
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

	onScriptLoaded(me) {
		me.linkHandler = window.Plaid.create({
			clientName: me.client_name,
			env: me.plaid_env,
			key: me.plaid_public_key,
			onSuccess: me.plaid_success,
			product: me.product
		})
	}

	onScriptError(error) {
		console.error('There was an issue loading the link-initialize.js script');
		console.log(error);
	}

	plaid_success(token, response) {
		const me = this;

		frappe.prompt({
			fieldtype:"Link", 
			options: "Company",
			label:__("Company"),
			fieldname:"company",
			reqd:1
		}, (data) => {
			me.company = data.company;
			frappe.xcall('erpnext.erpnext_integrations.doctype.plaid_settings.plaid_settings.add_institution', {token: token, response: response})
			.then((result) => {
				frappe.xcall('erpnext.erpnext_integrations.doctype.plaid_settings.plaid_settings.add_bank_accounts', {response: response,
					bank: result, company: me.company})
			})
			.then((result) => {
				frappe.show_alert({message:__("Bank accounts added"), indicator:'green'});
			})
		}, __("Select a company"), __("Continue"));
	}
}