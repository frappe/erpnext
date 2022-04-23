<template>
	<div
		class="marketplace-page"
		:data-page-name="page_name"
	>
		<search-input
			:placeholder="search_placeholder"
			:on_search="set_route_and_get_items"
			v-model="search_value"
		>
		</search-input>

		<h5>{{ page_title }}</h5>

		<item-cards-container
			container_name="Search"
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
			items: [],
			category: frappe.get_route()[2],
			search_value: frappe.get_route()[3],
			item_id_fieldname: 'name',
			filters: {},

			// Constants
			search_placeholder: __('Search for anything ...'),
			empty_state_message: __('')
		};
	},
	computed: {
		page_title() {
			return this.items.length
				? __('Results for "{0}" {1}', [
					this.search_value,
					this.category !== 'All' ? __('in category {0}', [this.category]) : ''
				  ])
				: __('No Items found.');
		}
	},
	created() {
		this.get_items();
	},
	methods: {
		get_items() {
			if (this.category !== 'All') {
				this.filters['hub_category'] = this.category;
			}
			hub.call('get_items', {
				keyword: this.search_value,
				filters: this.filters
			})
			.then((items) => {
				this.items = items;
			})
		},

		set_route_and_get_items() {
			frappe.set_route('marketplace', 'search', this.category, this.search_value);
			this.get_items();
		},

		go_to_item_details_page(hub_item_name) {
			frappe.set_route(`marketplace/item/${hub_item_name}`);
		}
	}
}
</script>

<style scoped></style>
