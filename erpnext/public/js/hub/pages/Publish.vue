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

		<div class="flex justify-between align-flex-end margin-bottom">
			<h5>{{ page_title }}</h5>

			<button class="btn btn-primary btn-sm publish-items"
				:disabled="no_selected_items"
				@click="publish_selected_items"
			>
				<span>{{ publish_button_text }}</span>
			</button>
		</div>

		<item-cards-container
			:container_name="page_title"
			:items="selected_items"
			:item_id_fieldname="item_id_fieldname"
			:is_local="true"
			:editable="true"
			@remove-item="remove_item_from_selection"

			:empty_state_message="empty_state_message"
			:empty_state_bordered="true"
			:empty_state_height="80"
		>
		</item-cards-container>

		<p class="text-muted">{{ valid_items_instruction }}</p>

		<search-input
			:placeholder="search_placeholder"
			:on_search="get_valid_items"
			v-model="search_value"
		>
		</search-input>

		<item-cards-container
			:items="valid_items"
			:item_id_fieldname="item_id_fieldname"
			:is_local="true"
			:on_click="show_publishing_dialog_for_item"
		>
		</item-cards-container>
	</div>
</template>

<script>
import NotificationMessage from '../components/NotificationMessage.vue';
import { ItemPublishDialog } from '../components/item_publish_dialog';

export default {
	name: 'publish-page',
	components: {
		NotificationMessage
	},
	data() {
		return {
			page_name: frappe.get_route()[1],
			valid_items: [],
			selected_items: [],
			items_data_to_publish: {},
			search_value: '',
			item_id_fieldname: 'item_code',

			// Constants
			// TODO: multiline translations don't work
			page_title: __('Publish Items'),
			search_placeholder: __('Search Items ...'),
			empty_state_message: __('No Items selected yet. Browse and click on items below to publish.'),
			valid_items_instruction: __('Only items with an image and description can be published. Please update them if an item in your inventory does not appear.'),
			last_sync_message: (hub.settings.last_sync_datetime)
				? __('Last sync was {0}.', [`<a href="#marketplace/profile">${comment_when(hub.settings.last_sync_datetime)}</a>`]) +
				  ` <a href="#marketplace/published-items">${__('See your Published Items.')}</a>`
				: ''
		};
	},
	computed: {
		no_selected_items() {
			return this.selected_items.length === 0;
		},

		publish_button_text() {
			const number = this.selected_items.length;
			let text = __('Publish');
			if(number === 1) {
				text = __('Publish 1 Item');
			}
			if(number > 1) {
				text = __('Publish {0} Items', [number]);
			}
			return text;
		},

		items_dict() {
			let items_dict = {};
			this.valid_items.map(item => {
				items_dict[item[this.item_id_fieldname]] = item
			})

			return items_dict;
		},
	},
	created() {
		this.get_valid_items();
		this.make_publishing_dialog();
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

		publish_selected_items() {
			frappe.call(
			'erpnext.hub_node.api.publish_selected_items',
				{
					items_to_publish: this.selected_items
				}
			)
			.then((r) => {
				this.selected_items = [];
				return frappe.db.get_doc('Marketplace Settings');
			})
			.then(doc => {
				hub.settings = doc;
				this.add_last_sync_message();
			});
		},

		add_last_sync_message() {
			this.last_sync_message = __('Last sync was {0}.',
				[`<a href="#marketplace/profile">${comment_when(hub.settings.last_sync_datetime)}</a>`]
			) + `<a href="#marketplace/published-items">${__('See your Published Items')}</a>.`;
		},

		clear_last_sync_message() {
			this.last_sync_message = '';
		},

		remove_item_from_selection(item_code) {
			this.selected_items = this.selected_items
				.filter(item => item.item_code !== item_code);
		},

		make_publishing_dialog() {
			this.item_publish_dialog = ItemPublishDialog(
				{
					fn: (values) => {
						this.add_item_to_publish(values);
						this.item_publish_dialog.hide();
					}
				},
				{
					fn: () => {
						const values = this.item_publish_dialog.get_values(true);
						this.update_items_data_to_publish(values);
					}
				}
			);
		},

		add_item_to_publish(values) {
			this.update_items_data_to_publish(values);

			const item_code  = values.item_code;
			let item_doc = this.items_dict[item_code];

			const item_to_publish = Object.assign({}, item_doc, values);
			this.selected_items.push(item_to_publish);
		},

		update_items_data_to_publish(values) {
			this.items_data_to_publish[values.item_code] = values;
		},

		show_publishing_dialog_for_item(item_code) {
			let item_data = this.items_data_to_publish[item_code];
			if(!item_data) { item_data = { item_code }; };

			this.item_publish_dialog.clear();

			const item_doc = this.items_dict[item_code];
			if(item_doc) {
				this.item_publish_dialog.fields_dict.image_list.set_data(
					item_doc.attachments.map(attachment => attachment.file_url)
				);
			}

			this.item_publish_dialog.set_values(item_data);
			this.item_publish_dialog.show();
		}
	}
}
</script>

<style scoped></style>
