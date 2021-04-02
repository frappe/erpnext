<template>
	<div
		class="marketplace-page"
		:data-page-name="page_name"
	>
		<section-header>
			<div>
				<h5>{{ __('Published Items') }}</h5>
				<p v-if="items.length"
					class="text-muted margin-bottom">
					{{ __('You can publish upto 200 items.') }}
				</p>
			</div>

			<button v-if="items.length"
				class="btn btn-default btn-xs publish-items"
				v-route="'marketplace/publish'"
			>
				<span>{{ __('Publish More Items') }}</span>
			</button>

		</section-header>

		<item-cards-container
			:container_name="__('Published Items')"
			:items="items"
			:item_id_fieldname="item_id_fieldname"
			:on_click="go_to_item_details_page"
			:empty_state_message="__('You haven\'t published any items yet.')"
			:empty_state_action="publish_page_action"
		>
		</item-cards-container>
	</div>
</template>

<script>
export default {
	data() {
		return {
			page_name: frappe.get_route()[1],
			items: [],
			item_id_fieldname: 'name',

			publish_page_action: {
				label: __('Publish Your First Items'),
				on_click: () => {
					frappe.set_route(`marketplace/publish`);
				}
			}
		};
	},
	created() {
		this.get_items();
	},
	methods: {
		get_items() {
			hub.call('get_items', {
				filters: {
					hub_seller: hub.settings.hub_seller_name
				}
			})
			.then((items) => {
				this.items = items;
			})
		},

		go_to_item_details_page(hub_item_name) {
			frappe.set_route(`marketplace/item/${hub_item_name}`);
		}
	}
}
</script>

<style scoped></style>
