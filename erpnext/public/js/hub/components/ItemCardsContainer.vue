<template>
	<div>
		<empty-state
			v-if="items.length === 0"
			:message="empty_state_message"
			:bordered="true"
			:height="80"
		>
		</empty-state>
		<item-card
			v-for="item in items"
			:key="item[item_id]"
			:item="item"
			:is_local="is_local"
		>
		</item-card>
	</div>
</template>

<script>
import ItemCard from './ItemCard.vue';
import EmptyState from './EmptyState.vue';

export default {
	name: 'item-cards-container',
	props: {
		'items': Array,
		'is_local': Boolean,

		'empty_state_message': String,
		'empty_state_height': Number,
		'empty_state_bordered': Boolean
	},
	components: {
		ItemCard,
		EmptyState
	},
	computed: {
		item_id() {
			return this.is_local ? 'item_code' : 'hub_item_code';
		}
	},
	watch: {
		items() {
			frappe.dom.handle_broken_images($(this.$el));
		}
	}
}
</script>

<style scoped></style>
