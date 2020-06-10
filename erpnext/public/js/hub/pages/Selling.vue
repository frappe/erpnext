<template>
	<div>
		<section-header>
			<h4>{{ __('Selling') }}</h4>
		</section-header>
		<div class="row" v-if="items && items.length">
			<div class="col-md-7"
				style="margin-bottom: 30px;"
				v-for="item of items"
				:key="item.name"
			>
				<item-list-card
					:item="item"
				>
					<div slot="subtitle">
						<span class="text-muted">{{ __('{0} conversations', [item.received_messages.length]) }}</span>
					</div>
				</item-list-card>
				<div class="hub-list-item" v-for="(message, index) in item.received_messages" :key="index"
					v-route="'marketplace/selling/' + message.buyer + '/' + item.name"
				>
					<div class="hub-list-left">
						<div class="hub-list-body">
							<div class="hub-list-title">
								{{ message.buyer_name }}
							</div>
							<div class="hub-list-subtitle">
								{{ message.sender }}: {{ message.message | striphtml }}
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
		<empty-state v-else :message="__('This page keeps track of your items in which buyers have showed some interest.')" :centered="false" />
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
			return hub.call('get_selling_items_for_messages');
		}
	}
}
</script>
