<template>
	<div ref="sidebar-container">
		<ul class="list-unstyled hub-sidebar-group" data-nav-buttons>
			<li class="hub-sidebar-item" v-for="item in items" :key="item.label" v-route="item.route" v-show="item.condition === undefined || item.condition()">
				{{ item.label }}
			</li>
		</ul>
		<ul class="list-unstyled hub-sidebar-group" data-categories>
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
			items: [
				{
					label: __('Browse'),
					route: 'marketplace/home'
				},
				{
					label: __('Become a Seller'),
					action: this.show_register_dialog,
					condition: () => !hub.settings.registered
				},
				{
					label: __('Saved Products'),
					route: 'marketplace/saved-products',
					condition: () => hub.settings.registered
				},
				{
					label: __('Your Profile'),
					route: 'marketplace/profile',
					condition: () => hub.settings.registered
				},
				{
					label: __('Your Products'),
					route: 'marketplace/my-products',
					condition: () => hub.settings.registered
				},
				{
					label: __('Publish Products'),
					route: 'marketplace/publish',
					condition: () => hub.settings.registered
				},
				{
					label: __('Selling'),
					route: 'marketplace/selling',
					condition: () => hub.settings.registered
				},
				{
					label: __('Buying'),
					route: 'marketplace/buying',
					condition: () => hub.settings.registered
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
		}
	}
}
</script>
