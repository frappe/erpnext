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

const handleImage = (el, src) => {
	let img = new Image();
	// add loading class
	el.src = '';
	el.classList.add('img-loading');

	img.onload = () => {
		// image loaded, remove loading class
		el.classList.remove('img-loading');
		// set src
		el.src = src;
	}
	img.onerror = () => {
		el.classList.remove('img-loading');
		el.classList.add('no-image');
		el.src = null;
	}
	img.src = src;
}

Vue.directive('img-src', {
	bind(el, binding) {
		handleImage(el, binding.value);
	},
	update(el, binding) {
		if (binding.value === binding.oldValue) return;
		handleImage(el, binding.value);
	}
});
