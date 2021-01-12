<template>
	<div
		class="marketplace-page"
		:data-page-name="page_name"
	>
		<h5>{{ page_title }}</h5>
		<p v-if="items.length"
			class="text-muted margin-bottom">
			{{ __('You can Feature upto 8 items.') }}
		</p>

		<item-cards-container
			:container_name="page_title"
			:items="items"
			:item_id_fieldname="item_id_fieldname"
			:on_click="go_to_item_details_page"
			:editable="true"
			@remove-item="on_item_remove"
			:empty_state_message="empty_state_message"
		>
		</item-cards-container>
	</div>
</template>

<script>
export default {
	name: 'featured-items-page',
	data() {
		return {
			page_name: frappe.get_route()[1],
			items: [],
			item_id_fieldname: 'name',

			// Constants
			page_title: __('Your Featured Items'),
			empty_state_message: __('No featured items yet. Got to your {0} and feature up to eight items that you want to highlight to your customers.',
				[`<a href="#marketplace/published-items">${__("Published Items")}</a>`])
		};
	},
	created() {
		this.get_items();
	},
	methods: {
		get_items() {
			hub.call(
				'get_featured_items_of_seller', {},
				'action:item_feature'
			)
			.then((items) => {
				this.items = items;
			})
		},

		go_to_item_details_page(hub_item_name) {
			frappe.set_route(`marketplace/item/${hub_item_name}`);
		},

		on_item_remove(hub_item_name) {
			const grace_period = 5000;
			let reverted = false;
			let alert;

			const undo_remove = () => {
				this.toggle_item(hub_item_name);;
				reverted = true;
				alert.hide();
				return false;
			}

			const item_name = this.items.filter(item => item.hub_item_name === hub_item_name);

			alert_message = __('{0} removed. {1}', [item_name, 
				`<a href="#" data-action="undo-remove"><b>${__('Undo')}</b></a>`]);
			alert = frappe.show_alert(alert_message, grace_period / 1000,
				{
					'undo-remove': undo_remove.bind(this)
				}
			);

			this.toggle_item(hub_item_name, false);

			setTimeout(() => {
				if(!reverted) {
					this.remove_item_from_featured_items(hub_item_name);
				}
			}, grace_period);
		},

		remove_item_from_featured_items(hub_item_name) {
			erpnext.hub.trigger('action:item_feature');
			hub.call('remove_item_from_seller_featured_items', {
				hub_item_name,
				hub_user: frappe.session.user
			})
			.then(() => {
				this.get_items();
			})
			.catch(e => {
				console.log(e);
			});
		},

		// By default show
		toggle_item(hub_item_name, show=true) {
			this.items = this.items.map(item => {
				if(item.name === hub_item_name) {
					item.seen = show;
				}
				return item;
			});
		}
	}
}
</script>

<style scoped></style>
