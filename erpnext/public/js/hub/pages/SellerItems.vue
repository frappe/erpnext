<template>
	<div
		class="marketplace-page"
		:data-page-name="page_name"
		v-if="init || items.length"
	>
		<h5>{{ item_container_heading }}</h5>
		<item-cards-container
			:container_name="item_container_heading"
			:items="items"
			:item_id_fieldname="item_id_fieldname"
			:on_click="go_to_item_details_page"
		>
		</item-cards-container>
	</div>
</template>

<script>
export default {
	name: 'seller-items-page',
	data() {
		return {
			page_name: frappe.get_route()[1],
			seller_company: frappe.get_route()[2],

			init: true,
			items:[],
			item_id_fieldname: 'name',
		};
	},
	created() {
		this.get_seller_and_items();
	},
	computed: {
		item_container_heading() {
			return __('Items by ' + this.seller_company);
		}
	},
	methods: {
		get_seller_and_items() {
			hub.call(
				'get_items',
				{ company: this.seller_company }
			).then(data => {
				this.init = false;
				this.items = data;
			});
		},

		go_to_item_details_page(hub_item_name) {
			frappe.set_route(`marketplace/item/${hub_item_name}`);
		}
	}
}
</script>

<style scoped></style>
