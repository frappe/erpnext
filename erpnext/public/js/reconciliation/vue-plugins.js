import Vue from 'vue/dist/vue.js';

Vue.prototype.__ = window.__;
Vue.prototype.frappe = window.frappe;

Vue.directive('route', {
	bind(el, binding) {
		const route = binding.value;
		if (!route) return;
		el.classList.add('cursor-pointer');
		el.dataset.route = route;
		el.addEventListener('click', () => frappe.set_route(route));
	},
	unbind(el) {
		el.classList.remove('cursor-pointer');
	}
});