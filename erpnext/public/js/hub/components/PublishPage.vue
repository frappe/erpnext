<template>
	<div
		class="marketplace-page"
		:data-page-name="page_name"
	>
		<notification-message
			v-if="last_sync_message"
			:message="last_sync_message"
			@remove-message="clear_last_sync_message"
		></notification-message>

		<div class="flex justify-between align-flex-end">
			<h5>{{ page_title }}</h5>

			<button class="btn btn-primary btn-sm publish-items"
				:disabled="no_selected_items">
				<span>{{ publish_button_text }}</span>
			</button>
		</div>

		<item-cards-container
			:items="selected_items"
			:is_local="true"
			:empty_state_message="empty_state_message"
			:empty_state_bordered="true"
			:empty_state_height="80"
		>
		</item-cards-container>

		<p class="text-muted">{{ valid_products_instruction }}</p>

		<search-input
			:placeholder="search_placeholder"
			:on_search="get_valid_items"
			v-model="search_value"
		>
		</search-input>

		<item-cards-container
			:items="valid_items"
			:is_local="true"
		>
		</item-cards-container>
	</div>
</template>

<script>
import SearchInput from './SearchInput.vue';
import ItemCardsContainer from './ItemCardsContainer.vue';
import NotificationMessage from './NotificationMessage.vue';

export default {
	name: 'publish-page',
	data() {
		return {
			page_name: frappe.get_route()[1],
			valid_items: [],
			selected_items: [],
			search_value: '',

			// Constants
			page_title: __('Publish Products'),
			search_placeholder: __('Search Items ...'),
			empty_state_message: __(`No Items selected yet.
				Browse and click on products below to publish.`),
			valid_products_instruction: __(`Only products with an image, description
				and category can be published. Please update them if an item in your
				inventory does not appear.`),
			last_sync_message: (hub.settings.last_sync_datetime)
				? __(`Last sync was
				<a href="#marketplace/profile">
					${comment_when(hub.settings.last_sync_datetime)}</a>.
				<a href="#marketplace/my-products">
					See your Published Products</a>.`)
				: ''
		};
	},
	components: {
		SearchInput,
		ItemCardsContainer,
		NotificationMessage
	},
	computed: {
		no_selected_items() {
			return this.selected_items.length === 0;
		},

		publish_button_text() {
			const number = this.selected_items.length;
			let text = 'Publish';
			if(number === 1) {
				text = 'Publish 1 Product';
			}
			if(number > 1) {
				text = `Publish ${number} Products`;
			}
			return __(text);
		}
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
		},

		clear_last_sync_message() {
			this.last_sync_message = '';
		}
	}
}
</script>

<style scoped></style>
