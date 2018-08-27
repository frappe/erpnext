<template>
	<div
		class="marketplace-page"
		:data-page-name="page_name"
	>
		<h5>{{ page_title }}</h5>

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
import ItemCardsContainer from '../components/ItemCardsContainer.vue';

export default {
	name: 'saved-products-page',
	data() {
		return {
			page_name: frappe.get_route()[1],
			items: [],
			item_id_fieldname: 'name',

			// Constants
			page_title: __('Saved Products'),
			empty_state_message: __(`You haven't favourited any items yet.`)
		};
	},
	components: {
		ItemCardsContainer
	},
	created() {
		this.get_items();
	},
	methods: {
		get_items() {
			hub.call(
				'get_favourite_items_of_seller',
				{
					hub_seller: hub.settings.company_email
				},
				'action:item_favourite'
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

			alert = frappe.show_alert(__(`<span>${hub_item_name} removed.
				<a href="#" data-action="undo-remove"><b>Undo</b></a></span>`),
				grace_period/1000,
				{
					'undo-remove': undo_remove.bind(this)
				}
			);

			this.toggle_item(hub_item_name, false);

			setTimeout(() => {
				if(!reverted) {
					this.remove_item_from_saved_products(hub_item_name);
				}
			}, grace_period);
		},

		remove_item_from_saved_products(hub_item_name) {
			erpnext.hub.trigger('action:item_favourite');
			hub.call('remove_item_from_seller_favourites', {
				hub_item_name,
				hub_seller: hub.settings.company_email
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
