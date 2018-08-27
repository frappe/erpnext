<template>
	<div>
		<section-header>
			<h4>{{ __('Selling') }}</h4>
		</section-header>
		<div class="row">
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
					v-route="'marketplace/selling/' + message.buyer_email + '/' + item.name"
				>
					<div class="hub-list-left">
						<div class="hub-list-body">
							<div class="hub-list-title">
								{{ message.buyer }}
							</div>
							<div class="hub-list-subtitle">
								{{ message.sender }}: {{ message.content }}
							</div>
						</div>
					</div>
				</div>
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
				console.log(items);
			});
	},
	methods: {
		get_items_for_messages() {
			return hub.call('get_selling_items_for_messages');
		}
	}
}
</script>
