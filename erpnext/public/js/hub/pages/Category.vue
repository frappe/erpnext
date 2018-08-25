<template>
	<div
		class="marketplace-page"
		:data-page-name="page_name"
	>
		<h5>{{ page_title }}</h5>

		<item-cards-container
			:container_name="page_title"
			:items="items"
			:item_id_fieldname="item_id_fieldname"
			:on_click="go_to_item_details_page"
			:empty_state_message="empty_state_message"
		>
		</item-cards-container>
	</div>
</template>

<script>
import ItemCardsContainer from '../components/ItemCardsContainer.vue';

export default {
	name: 'saved-products-page',
	components: {
		ItemCardsContainer
	},
	data() {
		return {
			page_name: frappe.get_route()[1],
			category: frappe.get_route()[2],
			items: [],
			item_id_fieldname: 'hub_item_code',

			// Constants
			empty_state_message: __(`No products in this category yet.`)
		};
	},
	computed: {
		page_title() {
			return __(this.category);
		}
	},
	created() {
		this.get_items();
	},
	methods: {
		get_items() {
			hub.call('get_items', {
				filters: {
					hub_category: this.category
				}
			})
			.then((items) => {
				this.items = items;
			})
		},

		go_to_item_details_page(hub_item_code) {
			frappe.set_route(`marketplace/item/${hub_item_code}`);
		}
	}
}
</script>

<style scoped></style>
