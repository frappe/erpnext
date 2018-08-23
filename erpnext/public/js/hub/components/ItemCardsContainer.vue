<template>
	<div>
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

export default {
	name: 'item-cards-container',
	props: ['items', 'is_local'],
	components: {
		ItemCard
	},
	computed: {
		item_id() {
			return this.is_local ? 'item_code' : 'hub_item_code';
		}
	}
}
</script>

<style scoped></style>
