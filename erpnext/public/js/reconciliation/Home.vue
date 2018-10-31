<template>
	<div ref="bankreconciliation" class="bankreconciliation" :data-page-name="current_page">
		<component 
			:is="current_page.component" 
			v-bind="{ getBankAccounts }" 
			:company='company'
			:accounts='accounts'
			>
		</component>
	</div>
</template>

<script>

import Dashboard from './pages/Dashboard.vue';
import Upload from './pages/Upload.vue';
import Reconciliation from './pages/Reconciliation.vue';

function get_route_map() {
	return {
		'bankreconciliation/home': {
			'component': Dashboard
		},
		'bankreconciliation/upload': {
			'component': Upload
		},
		'bankreconciliation/reconciliation': {
			'component': Reconciliation
		}
	}
}
export default {
	props: ['initCompany'],
	components: {

	},
	data() {
		return {
			current_page: this.get_current_page(),
			company: this.initCompany,
			accounts: []
		}
	},
	created() {
		erpnext.bankreconciliation.on('company_changed', (e) => {
			this.company = e;
		})
	},
	mounted() {
		frappe.route.on('change', () => {
			if (frappe.get_route()[0] === 'bankreconciliation') {
				this.set_current_page();
				frappe.utils.scroll_to(0);
				$("body").attr("data-route", frappe.get_route_str());
			}
		});
	},
	methods: {
		set_current_page() {
			this.current_page = this.get_current_page();
		},
		get_current_page() {
			const route_map = get_route_map();
			const route = frappe.get_route_str();
			if (route_map[route]) {
				return route_map[route];
			} else {
				return route_map[route.substring(0, route.lastIndexOf('/')) + '/*'] || route_map['not_found']
			}
		},
		getBankAccounts() {
			frappe.db.get_list('Bank Account', {
				fields: ['name', 'bank', 'bank_account_no', 'iban', 'branch_code', 'swift_number'],
				filters: {'is_company_account': 1, 'company': this.company}
			}).then((accounts) => {
				this.accounts = accounts;
			})
		}
	}
}
</script>
