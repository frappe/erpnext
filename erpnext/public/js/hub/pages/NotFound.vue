<template>
	<div
		class="marketplace-page"
		:data-page-name="page_name"
	>
		<empty-state
			:message="empty_state_message"
			:height="500"
			:action="action"
		>
		</empty-state>

	</div>
</template>

<script>
export default {
	name: 'not-found-page',
	data() {
		return {
			page_name: 'not-found',
			action: {
				label: __('Back to Home'),
				on_click: () => {
					frappe.set_route(`marketplace/home`);
				}
			},

			// Constants
			empty_state_message: __('Sorry! We could not find what you were looking for.')
		};
	},
}
</script>

<style scoped></style>
