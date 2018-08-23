<template>
	<div
		class="marketplace-page"
		:data-page-name="page_name"
	>
		<item-cards-container
			:items="valid_items"
			:is_local="1"
		>
		</item-cards-container>
	</div>
</template>

<script>
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
		ItemCardsContainer
	},
	// watch: {
	// 	// whenever search term changes, this function will run
	// 	question: function (newQuestion, oldQuestion) {
	// 		this.answer = 'Waiting for you to stop typing...'
	// 		this.debouncedGetAnswer()
	// 	}
	// },
	created() {
		this.get_valid_items();
	},
	methods: {
		get_valid_items() {
			var vm = this;

			frappe.call(
				'erpnext.hub_node.api.get_valid_items',
				{
					search_value: this.search_value
				}
			)
			.then(function (r) {
				vm.valid_items = r.message;
				frappe.dom.handle_broken_images(this.$wrapper);
			})
		}
	}
}
</script>

<style scoped></style>
