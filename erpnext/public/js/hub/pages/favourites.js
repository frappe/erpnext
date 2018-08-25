import SavedProductsPage from '../components/SavedProductsPage.vue';
import Vue from 'vue/dist/vue.js';

erpnext.hub.SavedProducts = class {
	constructor(parent) {
		this.$wrapper = $(`<div id="vue-area-saved">`).appendTo($(parent));

		new Vue({
			render: h => h(SavedProductsPage)
		}).$mount('#vue-area-saved');
	}

	show() {
		$('[data-page-name="saved-products"]').show();
	}

	hide() {
		$('[data-page-name="saved-products"]').hide();
	}
}
