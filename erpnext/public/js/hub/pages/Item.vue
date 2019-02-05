<template>
	<div
		class="marketplace-page"
		:data-page-name="page_name"
		v-if="init || item"
	>

		<detail-view
			:title="title"
			:image="image"
			:sections="sections"
			:menu_items="menu_items"
			:show_skeleton="init"
		>
			<detail-header-item slot="detail-header-item"
				:value="item_subtitle"
			></detail-header-item>
			<detail-header-item slot="detail-header-item"
				:value="item_views_and_ratings"
			></detail-header-item>

			<button v-if="primary_action" slot="detail-header-item"
				class="btn btn-primary btn-sm margin-top"
				@click="primary_action.action"
			>
				{{ primary_action.label }}
			</button>

		</detail-view>

		<review-area v-if="!init" :hub_item_name="hub_item_name"></review-area>
	</div>
</template>

<script>
import ReviewArea from '../components/ReviewArea.vue';
import { get_rating_html } from '../components/reviews';

export default {
	name: 'item-page',
	components: {
		ReviewArea
	},
	data() {
		return {
			page_name: frappe.get_route()[1],
			hub_item_name: frappe.get_route()[2],

			init: true,

			item: null,
			title: null,
			image: null,
			sections: [],

		};
	},
	computed: {
		is_own_item() {
			let is_own_item = false;
			if(this.item) {
				if(this.item.hub_seller === hub.settings.hub_seller_name) {
					is_own_item = true;
				}
			}
			return is_own_item;
		},
		menu_items(){
			return [
				{
					label: __('Save Item'),
					condition: hub.is_user_registered() && !this.is_own_item,
					action: this.add_to_saved_items
				},
				{
					label: __('Report this Item'),
					condition: !this.is_own_item,
					action: this.report_item
				},
				{
					label: __('Edit Details'),
					condition: hub.is_user_registered() && this.is_own_item,
					action: this.edit_details
				},
				{
					label: __('Unpublish Item'),
					condition: hub.is_user_registered() && this.is_own_item,
					action: this.unpublish_item
				}
			]
		},

		item_subtitle() {
			if(!this.item) {
				return '';
			}

			const dot_spacer = '<span aria-hidden="true"> · </span>';
			let subtitle_items = [comment_when(this.item.creation)];
			const rating = this.item.average_rating;

			if (rating > 0) {
				subtitle_items.push(rating + `<i class='fa fa-fw fa-star-o'></i>`)
			}

			subtitle_items.push(this.item.company);

			return subtitle_items;
		},

		item_views_and_ratings() {
			if(!this.item) {
				return '';
			}

			let stats = __('No views yet');
			if(this.item.view_count) {
				const views_message = __(`${this.item.view_count} Views`);

				const rating_html = get_rating_html(this.item.average_rating);
				const rating_count = this.item.no_of_ratings > 0 ? `${this.item.no_of_ratings} reviews` : __('No reviews yet');

				stats = [views_message, rating_html, rating_count];
			}

			return stats;
		},

		primary_action() {
			if (hub.is_user_registered()) {
				return {
					label: __('Contact Seller'),
					action: this.contact_seller.bind(this)
				}
			} else {
				return undefined;
			}
		}
	},
	created() {
		this.get_item_details();
	},
	mounted() {
		// To record a single view per session, (later)
		// erpnext.hub.item_view_cache = erpnext.hub.item_view_cache || [];
		// if (erpnext.hub.item_view_cache.includes(this.hub_item_name)) {
		// 	return;
		// }

		this.item_received.then(() => {
			setTimeout(() => {
				hub.call('add_item_view', {
					hub_item_name: this.hub_item_name
				})
				// .then(() => {
				// 	erpnext.hub.item_view_cache.push(this.hub_item_name);
				// });
			}, 5000);
		});
	},
	methods: {
		get_item_details() {
			this.item_received = hub.call('get_item_details', { hub_item_name: this.hub_item_name })
				.then(item => {
				this.init = false;
				this.item = item;

				this.build_data();
				this.make_dialogs();
			});
		},

		build_data() {
			this.title = this.item.item_name || this.item.name;
			this.image = this.item.image;

			this.sections = [
				{
					title: __('Item Description'),
					content: this.item.description
						? __(this.item.description)
						: __('No description')
				},
				{
					title: __('Seller Information'),
					content: this.item.seller_description
						? __(this.item.seller_description)
						: __('No description')
				}
			];
		},

		make_dialogs() {
			this.make_contact_seller_dialog();
			this.make_report_item_dialog();
		},

		add_to_saved_items() {
			hub.call('add_item_to_user_saved_items', {
				hub_item_name: this.hub_item_name,
				hub_user: frappe.session.user
			})
			.then(() => {
				const saved_items_link = `<b><a href="#marketplace/saved-items">${__('Saved')}</a></b>`
				frappe.show_alert(saved_items_link);
				erpnext.hub.trigger('action:item_save');
			})
			.catch(e => {
				console.error(e);
			});
		},

		make_contact_seller_dialog() {
			this.contact_seller_dialog = new frappe.ui.Dialog({
				title: __('Send a message'),
				fields: [
					{
						fieldname: 'to',
						fieldtype: 'Read Only',
						label: __('To'),
						default: this.item.company
					},
					{
						fieldtype: 'Text',
						fieldname: 'message',
						label: __('Message')
					}
				],
				primary_action: ({ message }) => {
					if (!message) return;

					hub.call('send_message', {
						hub_item: this.item.name,
						message
					})
						.then(() => {
							this.contact_seller_dialog.hide();
							frappe.set_route('marketplace', 'buying', this.item.name);
							erpnext.hub.trigger('action:send_message')
						});
				}
			});
		},

		make_report_item_dialog() {
			this.report_item_dialog = new frappe.ui.Dialog({
				title: __('Report Item'),
				fields: [
					{
						label: __('Why do think this Item should be removed?'),
						fieldtype: 'Text',
						fieldname: 'message'
					}
				],
				primary_action: ({ message }) => {
					hub.call('add_reported_item', { hub_item_name: this.item.name, message })
						.then(() => {
							d.hide();
							frappe.show_alert(__('Item Reported'));
						});
				}
			});
		},

		contact_seller() {
			this.contact_seller_dialog.show();
		},

		report_item() {
			if (!hub.is_seller_registered()) {
				frappe.throw(__('Please login as a Marketplace User to report this item.'));
			}
			this.report_item_dialog.show();
		},

		edit_details() {
			frappe.msgprint(__('This feature is under development...'));
		},

		unpublish_item() {
			frappe.msgprint(__('This feature is under development...'));
		}
	}
}
</script>

<style scoped></style>
