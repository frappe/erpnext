<template>
	<div>
		<section-header>
			<h4>{{ __('Buying') }}</h4>
		</section-header>
		<div class="row">
			<div class="col-md-7"
				v-for="item of items"
				:key="item.name"
			>
				<item-list-card
					:item="item"
					:message="item.recent_message"
					v-route="'marketplace/buying/' + item.name"
				/>
			</div>
		</div>
	</div>
</template>
<script>
import SectionHeader from '../components/SectionHeader.vue';
import ItemListCard from '../components/ItemListCard.vue';

export default {
	components: {
		SectionHeader,
		ItemListCard
	},
	data() {
		return {
			items: []
		}
	},
	created() {
		this.get_items_for_messages()
			.then(items => {
				this.items = items;
			});
	},
	methods: {
		get_items_for_messages() {
			return hub.call('get_buying_items_for_messages', {}, 'action:send_message');
		}
	}
}
</script>
