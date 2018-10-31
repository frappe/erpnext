<template>
	<div>
		<bank-accounts-container
			:container_name="page_title"
			:accounts="accounts"
			:account_id_fieldname="account_id_fieldname"
			:on_click="select_account"
			:empty_state_message="empty_state_message"
			:selected_account="selected_account"
		>
		</bank-accounts-container>
		
		<div v-show="selected_account.name !== undefined">
			<hr>
			<div ref="upload-container" class="upload-btn-container"></div>
			<div class="table-container"></div>

			<div v-show="datatable_not_empty">
				<button
					class="btn btn-primary btn-xl"
					@click="add_bank_entries">
					{{ __('Add bank entries') }}
				</button>
			</div>
		</div>

	</div>
</template>

<script>

import DataTable from 'frappe-datatable';
import BankAccountsContainer from '../components/BankAccountsContainer.vue';

export default {
	props: {
		company: String,
		accounts: Array,
		getBankAccounts: Function
	},
	components: {
		BankAccountsContainer
	},
	data() {
		return {
			account_id_fieldname: 'name',
			page_title: __('Accounts'),
			empty_state_message: __(`You haven't added any bank account yet.`),
			selected_account: {},
			bank_entries: {}
		}
	},
	created() {
		this.getBankAccounts();
	},
	mounted() {
		this.add_upload_section();
	},
	computed: {
		datatable_not_empty() {
			return Object.keys(this.bank_entries).length > 0
		}
	},
	methods: {
		add_upload_section() {
			let me = this;
			let wrapper = $(this.$refs['upload-container']);
			frappe.upload.make({
				parent: wrapper,
				args: {
					method: 'erpnext.accounts.doctype.bank_transaction.bank_transaction_upload.upload_bank_statement',
					allow_multiple: 0
				},
				no_socketio: true,
				sample_url: "e.g. http://example.com/somefile.csv",
				callback: function(attachment, r) {
					if (!r.exc && r.message) {
						me.bank_entries = new DataTable('.table-container', {
												columns: r.message.columns,
												data: r.message.data
											})
					}
				}
			})
		},

		select_account(account) {
			if (this.selected_account == account) {
				this.selected_account = {}
			} else {
				this.selected_account = account
			}
		},

		upload_file() {
			erpnext.bankreconciliation.upload_statement.show()
		},

		add_bank_entries() {
			console.log(this.bank_entries.datamanager)
			frappe.xcall('erpnext.accounts.doctype.bank_transaction.bank_transaction_upload.create_bank_entries', 
				{columns: this.bank_entries.datamanager.columns, data: this.bank_entries.datamanager.data, bank_account: this.selected_account}
			).then((result) => {
				console.log(result)
			})
		}

	}
};
</script>
<style lang="less" scoped>
button {
	margin-top: 35px;
}
</style>