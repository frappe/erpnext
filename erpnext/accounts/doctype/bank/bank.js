// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
frappe.provide('erpnext.integrations');

frappe.ui.form.on('Bank', {
	onload: function(frm) {
		add_fields_to_mapping_table(frm);
	},
	refresh: function(frm) {
		add_fields_to_mapping_table(frm);

		frappe.dynamic_link = { doc: frm.doc, fieldname: 'name', doctype: 'Bank' };

		frm.toggle_display(['address_html','contact_html'], !frm.doc.__islocal);

		if (frm.doc.__islocal) {
			frm.set_df_property('address_and_contact', 'hidden', 1);
			frappe.contacts.clear_address_and_contact(frm);
		}
		else {
			frm.set_df_property('address_and_contact', 'hidden', 0);
			frappe.contacts.render_address_and_contact(frm);
		}
		if (frm.doc.plaid_access_token) {
			frm.add_custom_button(__('Refresh Plaid Link'), () => {
				new erpnext.integrations.refreshPlaidLink(frm.doc.plaid_access_token);
			});
		}
	}
});


let add_fields_to_mapping_table = function (frm) {
	let options = [];

	frappe.model.with_doctype("Bank Transaction", function() {
		let meta = frappe.get_meta("Bank Transaction");
		meta.fields.forEach(value => {
			if (!["Section Break", "Column Break"].includes(value.fieldtype)) {
				options.push(value.fieldname);
			}
		});
	});

	frappe.meta.get_docfield("Bank Transaction Mapping", "bank_transaction_field",
		frm.doc.name).options = options;

	frm.fields_dict.bank_transaction_mapping.grid.refresh();
};

erpnext.integrations.refreshPlaidLink = class refreshPlaidLink {
	constructor(access_token) {
		this.access_token = access_token;
		this.plaidUrl = 'https://cdn.plaid.com/link/v2/stable/link-initialize.js';
		this.init_config();
	}

	async init_config() {
		this.plaid_env = await frappe.db.get_single_value('Plaid Settings', 'plaid_env');
		this.token = await this.get_link_token_for_update();
		this.init_plaid();
	}

	async get_link_token_for_update() {
		const token = frappe.xcall(
			'erpnext.erpnext_integrations.doctype.plaid_settings.plaid_settings.get_link_token_for_update',
			{ access_token: this.access_token }
		)
		if (!token) {
			frappe.throw(__('Cannot retrieve link token for update. Check Error Log for more information'));
		}
		return token;
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
				me.onScriptError(error);
			});
	}

	loadScript(src) {
		return new Promise(function (resolve, reject) {
			if (document.querySelector("script[src='" + src + "']")) {
				resolve();
				return;
			}
			const el = document.createElement('script');
			el.type = 'text/javascript';
			el.async = true;
			el.src = src;
			el.addEventListener('load', resolve);
			el.addEventListener('error', reject);
			el.addEventListener('abort', reject);
			document.head.appendChild(el);
		});
	}

	onScriptLoaded(me) {
		me.linkHandler = Plaid.create({
			env: me.plaid_env,
			token: me.token,
			onSuccess: me.plaid_success
		});
	}

	onScriptError(error) {
		frappe.msgprint(__("There was an issue connecting to Plaid's authentication server. Check browser console for more information"));
		console.log(error);
	}

	plaid_success(token, response) {
		frappe.show_alert({ message: __('Plaid Link Updated'), indicator: 'green' });
	}
};
