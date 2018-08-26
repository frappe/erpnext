<template>
	<div class="hub-page-container">
		<component :is="current_page"></component>
	</div>
</template>
<script>
import Home from './pages/Home.vue';
import SavedProducts from './pages/SavedProducts.vue';
import Publish from './pages/Publish.vue';
import Category from './pages/Category.vue';
import Search from './pages/Search.vue';
import PublishedProducts from './pages/PublishedProducts.vue';

const route_map = {
	'marketplace/home': Home,
	'marketplace/saved-products': SavedProducts,
	'marketplace/publish': Publish
}

export default {
	data() {
		return {
			current_page: this.get_current_page()
		}
	},
	mounted() {
		frappe.route.on('change', () => {
			this.set_current_page();
		});
	},
	methods: {
		set_current_page() {
			this.current_page = this.get_current_page();
		},
		get_current_page() {
			return route_map[frappe.get_route_str()];
		}
	}
}
</script>
