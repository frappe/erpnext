<template>
	<div
		class="marketplace-page"
		:data-page-name="page_name"
	>
		<search-input
			:placeholder="search_placeholder"
			:on_search="set_search_route"
			v-model="search_value"
		/>

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
export default {
	data() {
		return {
			page_name: frappe.get_route()[1],
			category: frappe.get_route()[2],
			items: [],
			item_id_fieldname: 'name',

			// Constants
			empty_state_message: __('No items in this category yet.'),

			search_value: '',

			// Constants
			search_placeholder: __('Search for anything ...'),

		};
	},
	computed: {
		page_title() {
			return __(this.category);
		}
	},
	created() {
		this.search_value = '';
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

		go_to_item_details_page(hub_item_name) {
			frappe.set_route(`marketplace/item/${hub_item_name}`);
		},

		set_search_route() {
			frappe.set_route('marketplace', 'search', this.category, this.search_value);
		},
	}
}
</script>

<style scoped></style>
