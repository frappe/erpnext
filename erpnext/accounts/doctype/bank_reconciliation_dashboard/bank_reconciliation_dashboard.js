// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.accounts");


frappe.ui.form.on('Bank Reconciliation Dashboard', {
	refresh: function(frm) {
		frm.disable_save();
		toggle_sidebar(frm);
		frm.page.add_menu_item(__("Toggle Sidebar"), function() {
			toggle_sidebar(frm);
		});

		new erpnext.accounts.newInstitution(frm);
	},
	import_data: function(frm) {
		new erpnext.accounts.bankTransactionUpload(frm);
	},
	sync_data: function(frm) {
		new erpnext.accounts.bankTransactionSync(frm);
	},
	reconcile_data: function(frm) {
		console.log("test")
	},
	
});

let toggle_sidebar = function(frm) {
	frm.sidebar.sidebar.toggle();
	frm.page.current_view.find('.layout-main-section-wrapper').toggleClass('col-md-10 col-md-12');
}

erpnext.accounts.bankTransactionUpload = class bankTransactionUpload {
	constructor(frm) {
		this.frm = frm;
		this.data = [];
		this.import_wrapper = $(frm.fields_dict['import_html'].wrapper);
		this.table_container = $(frm.fields_dict['table_container'].wrapper);

		const assets = [
			"/assets/frappe/css/frappe-datatable.css",
			"/assets/frappe/js/lib/clusterize.min.js",
			"/assets/frappe/js/lib/Sortable.min.js",
			"/assets/frappe/js/lib/frappe-datatable.js"
		];

		frappe.require(assets, () => {
			this.make();
		});
	}

	make() {
		let me = this;
		frappe.upload.make({
			parent: me.import_wrapper,
			args: {
				method: 'erpnext.accounts.doctype.bank_transaction.bank_transaction_upload.upload_bank_statement',
				allow_multiple: 0
			},
			no_socketio: true,
			sample_url: "e.g. http://example.com/somefile.csv",
			callback: function(attachment, r) {
				if (!r.exc && r.message) {
					me.data = r.message;
					me.setup_transactions_dom();
					me.create_datatable();
					me.bind_events();
				}
			}
		})
	}

	setup_transactions_dom() {
		this.table_container.append(`
			<div class="transactions-table"></div>
			<div class="transactions-btn margin-top text-right">
				<button class= "btn btn-primary btn-submit"> ${ __("Submit") } </button>
			</div>`)
	}

	create_datatable() {
		this.datatable = new DataTable('.transactions-table', {
							columns: this.data.columns,
							data: this.data.data
						})
	}

	bind_events() {
		this.table_container.on('click', '.transactions-btn', function() {
			console.log("Test")
		})
	}

	add_bank_entries() {
		frappe.xcall('erpnext.accounts.doctype.bank_transaction.bank_transaction_upload.create_bank_entries', 
			{columns: this.data.datamanager.columns, data: this.data.datamanager.data, bank_account: this.frm.doc.bank_account}
		).then((result) => {
			console.log(result)
		})
	}
}

erpnext.accounts.bankTransactionSync = class bankTransactionSync {
	constructor(frm) {
		this.frm = frm;
		this.data = [];
		this.import_wrapper = $(frm.fields_dict['import_html'].wrapper);
		this.table_container = $(frm.fields_dict['table_container'].wrapper);


		this.init_config()
		const assets = [
			"/assets/frappe/css/frappe-datatable.css",
			"/assets/frappe/js/lib/clusterize.min.js",
			"/assets/frappe/js/lib/Sortable.min.js",
			"/assets/frappe/js/lib/frappe-datatable.js"
		];

		frappe.require(assets, () => {
			this.make();
		});
	}

	init_config() {
		let me = this;
		frappe.xcall('erpnext.erpnext_integrations.doctype.plaid_settings.plaid_settings.plaid_configuration')
		.then(result => {
			me.plaid_env = result.plaid_env;
			me.plaid_public_key = result.plaid_public_key;
			me.client_name = result.client_name;
			me.sync_transactions()
		})
	}

	sync_transactions() {
		let me = this;
		frappe.db.get_value("Bank Account", me.frm.doc.bank_account, "bank", (v) => {
			frappe.xcall('erpnext.erpnext_integrations.doctype.plaid_settings.plaid_settings.sync_transactions', {
				bank: v['bank'],
				bank_account: me.frm.doc.bank_account
			})
			.then((result) => {
				console.log(result)
				me.get_transactions();
			})
		})
	}

	get_transactions() {
		let me = this;
		frappe.db.get_list('Bank Transaction', {
			fields: ['name', 'date', 'status', 'debit', 'credit', 'currency', 'description'],
			filters: {"docstatus": 1},
			or_filters: [['reference_number', '=', '']]

		}).then((transactions) => {
			me.transactions = transactions;
			console.log(me)
		})
	}

	make() {

	}
}

erpnext.accounts.newInstitution = class newInstitution {
	constructor(frm) {
		this.frm = frm;
		this.init_config()
	}

	init_config() {
		let me = this;
		frappe.xcall('erpnext.erpnext_integrations.doctype.plaid_settings.plaid_settings.plaid_configuration')
		.then(result => {
			if (result) {
				me.plaid_env = result.plaid_env;
				me.plaid_public_key = result.plaid_public_key;
				me.client_name = result.client_name;
				me.new_plaid_link()
			}
		})
	}

	plaid_success(token, response) {
		frappe.xcall('erpnext.erpnext_integrations.doctype.plaid_settings.plaid_settings.add_institution', {token: token, response: response})
		.then((result) => {
			frappe.xcall('erpnext.erpnext_integrations.doctype.plaid_settings.plaid_settings.add_bank_accounts', {response: response, bank: result})
		})
		.then((result) => {
			this.getBankAccounts();
		})
	}

	new_plaid_link() {
		let me = this;
		frappe.require('assets/js/frappe-vue.js', () => {
			new Vue({
				el: $(frm.fields_dict['new_institution'].wrapper),
				render(h) {
					return h(PlaidLink, {
						props: { 
							env: me.plaid_env,
							publicKey: me.plaid_public_key,
							clientName: me.client_name,
							product: ["transactions", "auth"],
							subtitle: "Test",
							plaidSuccess: me.plaid_success
						}
					})
				}
			});
		})
	}
}