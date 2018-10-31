<template>
	<div ref="sidebar-container">
		<ul class="list-unstyled bankreconciliation-sidebar-group" data-nav-buttons>
			<li class="bankreconciliation-sidebar-item" v-for="item in items" :key="item.label" v-route="item.route">
				{{ item.label }}
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
					label: __('Dashboard'),
					route: 'bankreconciliation/home'
				},
				{
					label: __('Statement upload'),
					route: 'bankreconciliation/upload'
				},
				{
					label: __('Bank reconciliation'),
					route: 'bankreconciliation/reconciliation',
				},
			]
		}
	},
	created() {
	},
	mounted() {
		this.update_sidebar_state();
		frappe.route.on('change', () => this.update_sidebar_state());
	},
	methods: {
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