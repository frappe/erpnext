<template>
	<div ref="sidebar-container">
		<ul class="list-unstyled hub-sidebar-group" data-nav-buttons>
			<li class="hub-sidebar-item" v-for="item in items" :key="item.label" v-route="item.route" v-show="item.condition === undefined || item.condition()">
				{{ item.label }}
			</li>
		</ul>
		<ul class="list-unstyled hub-sidebar-group" data-categories>
			<li class="hub-sidebar-item is-title bold text-muted">
				{{ __('Categories') }}
			</li>
			<li class="hub-sidebar-item" v-for="category in categories" :key="category.label" v-route="category.route">
				{{ category.label }}
			</li>
		</ul>
	</div>
</template>
<script>
export default {
	data() {
		return {
			hub_registered: hub.is_user_registered(),
			items: [
				{
					label: __('Browse'),
					route: 'marketplace/home'
				},
				{
					label: __('Saved Items'),
					route: 'marketplace/saved-items',
					condition: () => this.hub_registered
				},
				{
					label: __('Your Profile'),
					route: 'marketplace/profile',
					condition: () => this.hub_registered
				},
				{
					label: __('Your Items'),
					route: 'marketplace/published-items',
					condition: () => this.hub_registered
				},
				{
					label: __('Publish Items'),
					route: 'marketplace/publish',
					condition: () => this.hub_registered
				},
				{
					label: __('Selling'),
					route: 'marketplace/selling',
					condition: () => this.hub_registered
				},
				{
					label: __('Buying'),
					route: 'marketplace/buying',
					condition: () => this.hub_registered
				},
			],
			categories: []
		}
	},
	created() {
		this.get_categories()
			.then(categories => {
				this.categories = categories.map(c => {
					return {
						label: __(c.name),
						route: 'marketplace/category/' + c.name
					}
				});
				this.categories.unshift({
					label: __('All'),
					route: 'marketplace/home'
				});
				this.$nextTick(() => {
					this.update_sidebar_state();
				});
			});

		erpnext.hub.on('seller-registered', () => {
			this.hub_registered = true;
		})
	},
	mounted() {
		this.update_sidebar_state();
		frappe.route.on('change', () => this.update_sidebar_state());
	},
	methods: {
		get_categories() {
			return hub.call('get_categories');
		},
		update_sidebar_state() {
			const container = $(this.$refs['sidebar-container']);
			const route = frappe.get_route();
			const route_str = route.join('/');
			const part_route_str = route.slice(0, 2).join('/');
			const $sidebar_item = container.find(`[data-route="${route_str}"], [data-route="${part_route_str}"]`);

			const $siblings = container.find('[data-route]');
			$siblings.removeClass('active').addClass('text-muted');
			$sidebar_item.addClass('active').removeClass('text-muted');
		},
	}
}
</script>
