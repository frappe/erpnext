<template>
	<div class="item-cards-container">
		<empty-state
			v-if="items.length === 0"
			:message="empty_state_message"
			:action="empty_state_action"
			:bordered="true"
			:height="empty_state_height"
		/>
		<item-card
			v-for="item in items"
			:key="container_name + '_' +item[item_id_fieldname]"
			:item="item"
			:item_id_fieldname="item_id_fieldname"
			:is_local="is_local"
			:on_click="on_click"
			:allow_clear="editable"
			:seen="item.hasOwnProperty('seen') ? item.seen : true"
			@remove-item="$emit('remove-item', item[item_id_fieldname])"
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
		container_name: String,
		items: Array,
		item_id_fieldname: String,
		is_local: Boolean,
		on_click: Function,
		editable: Boolean,

		empty_state_message: String,
		empty_state_action: Object,
		empty_state_height: Number,
		empty_state_bordered: Boolean
	},
	components: {
		ItemCard,
		EmptyState
	},
	watch: {
		items() {
			// TODO: handling doesn't work
			frappe.dom.handle_broken_images($(this.$el));
		}
	}
}
</script>

<style scoped>
	.item-cards-container {
		margin: 0 -15px;
		overflow: overlay;
	}
</style>
