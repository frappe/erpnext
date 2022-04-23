import Vue from 'vue/dist/vue.js';

// Global components
import ItemCardsContainer from './components/ItemCardsContainer.vue';
import SectionHeader from './components/SectionHeader.vue';
import SearchInput from './components/SearchInput.vue';
import DetailView from './components/DetailView.vue';
import DetailHeaderItem from './components/DetailHeaderItem.vue';
import EmptyState from './components/EmptyState.vue';
import Image from './components/Image.vue';

Vue.prototype.__ = window.__;
Vue.prototype.frappe = window.frappe;

Vue.component('item-cards-container', ItemCardsContainer);
Vue.component('section-header', SectionHeader);
Vue.component('search-input', SearchInput);
Vue.component('detail-view', DetailView);
Vue.component('detail-header-item', DetailHeaderItem);
Vue.component('empty-state', EmptyState);
Vue.component('base-image', Image);

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

Vue.filter('striphtml', function (text) {
	return strip_html(text || '');
});