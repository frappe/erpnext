<template>
	<div class="hub-page-container">
		<component :is="current_page"></component>
	</div>
</template>

<script>

import Home from './pages/Home.vue';
import Search from './pages/Search.vue';
import Category from './pages/Category.vue';
import SavedProducts from './pages/SavedProducts.vue';
import PublishedProducts from './pages/PublishedProducts.vue';
import Item from './pages/Item.vue';
import Seller from './pages/Seller.vue';
import Publish from './pages/Publish.vue';
import Buying from './pages/Buying.vue';
import BuyingMessages from './pages/BuyingMessages.vue';
import Profile from './pages/Profile.vue';
import NotFound from './pages/NotFound.vue';

const route_map = {
	'marketplace/home': Home,
	'marketplace/search/:keyword': Search,
	'marketplace/category/:category': Category,
	'marketplace/item/:item': Item,
	'marketplace/seller/:seller': Seller,
	'marketplace/not-found': NotFound,

	// Registered seller routes
	'marketplace/profile': Profile,
	'marketplace/saved-products': SavedProducts,
	'marketplace/publish': Publish,
	'marketplace/my-products': PublishedProducts,
	'marketplace/buying': Buying,
	'marketplace/buying/:item': BuyingMessages,
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
			const curr_route = frappe.get_route_str();
			let route = Object.keys(route_map).filter(route => route == curr_route)[0];

			if (!route) {
				// find route by matching it with dynamic part
				const curr_route_parts = curr_route.split('/');
				const weighted_routes = Object.keys(route_map)
					.map(route_str => route_str.split('/'))
					.filter(route_parts => route_parts.length === curr_route_parts.length)
					.reduce((obj, route_parts) => {
						const key = route_parts.join('/');
						let weight = 0;
						route_parts.forEach((part, i) => {
							const curr_route_part = curr_route_parts[i];
							if (part === curr_route_part || curr_route_part.includes(':')) {
								weight += 1;
							}
						});

						obj[key] = weight;
						return obj;
					}, {});

				// get the route with the highest weight
				let weight = 0
				for (let key in weighted_routes) {
					const route_weight = weighted_routes[key];
					if (route_weight > weight) {
						route = key;
						weight = route_weight;
					}
				}
			}

			if (!route) {
				return NotFound;
			}

			return route_map[route];
		}
	}
}
</script>
