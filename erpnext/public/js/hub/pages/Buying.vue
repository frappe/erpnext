<template>
	<div>
		<section-header>
			<h4>{{ __('Buying') }}</h4>
		</section-header>
		<div class="row" v-if="items && items.length">
			<div class="col-md-7 margin-bottom"
				v-for="item of items"
				:key="item.name"
			>
				<item-list-card
					:item="item"
					v-route="'marketplace/buying/' + item.name"
				>
					<div slot="subtitle">
						<span>{{ get_sender(item.recent_message) }}: </span>
						<span>{{ item.recent_message.message | striphtml }}</span>
					</div>
				</item-list-card>
			</div>
		</div>
		<empty-state v-else :message="__('This page keeps track of items you want to buy from sellers.')" :centered="false" />
	</div>
</template>
<script>
import EmptyState from '../components/EmptyState.vue';
import SectionHeader from '../components/SectionHeader.vue';
import ItemListCard from '../components/ItemListCard.vue';

export default {
	components: {
		SectionHeader,
		ItemListCard,
		EmptyState
	},
	data() {
		return {
			items: null
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
		},
		get_sender(message) {
			return message.sender === frappe.session.user ? __('You') : (message.sender_name || message.sender);
		}
	}
}
</script>
