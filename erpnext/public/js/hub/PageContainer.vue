<template>
	<div class="hub-page-container">
		<component :is="current_page"></component>
	</div>
</template>

<script>

import Home from './pages/Home.vue';
import Search from './pages/Search.vue';
import Category from './pages/Category.vue';
import SavedItems from './pages/SavedItems.vue';
import PublishedItems from './pages/PublishedItems.vue';
import Item from './pages/Item.vue';
import Seller from './pages/Seller.vue';
import Publish from './pages/Publish.vue';
import Buying from './pages/Buying.vue';
import Selling from './pages/Selling.vue';
import Messages from './pages/Messages.vue';
import Profile from './pages/Profile.vue';
import NotFound from './pages/NotFound.vue';

function get_route_map() {
	const read_only_routes = {
		'marketplace/home': Home,
		'marketplace/search/:keyword': Search,
		'marketplace/category/:category': Category,
		'marketplace/item/:item': Item,
		'marketplace/seller/:seller': Seller,
		'marketplace/not-found': NotFound,
	}
	const registered_routes = {
		'marketplace/profile': Profile,
		'marketplace/saved-items': SavedItems,
		'marketplace/publish': Publish,
		'marketplace/published-items': PublishedItems,
		'marketplace/buying': Buying,
		'marketplace/buying/:item': Messages,
		'marketplace/selling': Selling,
		'marketplace/selling/:buyer/:item': Messages
	}

	return hub.is_seller_registered()
		? Object.assign({}, read_only_routes, registered_routes)
		: read_only_routes;
}

export default {
	data() {
		return {
			current_page: this.get_current_page()
		}
	},
	mounted() {
		frappe.route.on('change', () => {
			if (frappe.get_route()[0] === 'marketplace') {
				this.set_current_page();
				frappe.utils.scroll_to(0);
			}
		});
	},
	methods: {
		set_current_page() {
			this.current_page = this.get_current_page();
		},
		get_current_page() {
			const route_map = get_route_map();
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
							if (part === curr_route_part || part.includes(':')) {
								weight += 1;
							}
						});

						obj[key] = weight;
						return obj;
					}, {});

				// get the route with the highest weight
				for (let key in weighted_routes) {
					const route_weight = weighted_routes[key];
					if (route_weight === curr_route_parts.length) {
						route = key;
						break;
					} else {
						route = null;
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
