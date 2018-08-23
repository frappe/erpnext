<template>
	<div
		class="marketplace-page"
		:data-page-name="page_name"
	>
		<search-input
			placeholder="Search Items ..."
			:on_search="get_valid_items"
			v-model="search_value"
		>
		</search-input>
		<item-cards-container
			:items="valid_items"
			:is_local="1"
		>
		</item-cards-container>
	</div>
</template>

<script>
import SearchInput from './SearchInput.vue';
import ItemCardsContainer from './ItemCardsContainer.vue';

export default {
	name: 'publish-page',
	data() {
		return {
			page_name: frappe.get_route()[1],
			valid_items: [],
			search_value: ''
		};
	},
	components: {
		SearchInput,
		ItemCardsContainer
	},
	created() {
		this.get_valid_items();
	},
	methods: {
		get_valid_items() {
			frappe.call(
				'erpnext.hub_node.api.get_valid_items',
				{
					search_value: this.search_value
				}
			)
			.then((r) => {
				this.valid_items = r.message;
			})
		}
	}
}
</script>

<style scoped></style>
