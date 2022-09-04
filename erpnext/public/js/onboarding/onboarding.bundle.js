import Onboarding from './Onboarding.vue';

frappe.provide('erpnext.ui');


erpnext.ui.Onboarding = class {
	constructor({wrapper, page, module_data, regional_data}) {
		this.$wrapper = wrapper;
		let $container = $('<div>');
		$container.appendTo(this.$wrapper);
		this.page = page;
		$('.navbar').remove();
		$('.page-head').remove();

		let $vm = new Vue({
			el: $container.get(0),
			render: h => h(Onboarding, {
				props: {
					modules: module_data,
					regional_data: regional_data
				}
			}),
		});
	}

}