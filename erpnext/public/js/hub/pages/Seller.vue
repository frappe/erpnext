<template>
	<div
		class="marketplace-page"
		:data-page-name="page_name"
		v-if="init || profile"
	>
		<detail-view
			:title="title"
			:image="image"
			:sections="sections"
			:show_skeleton="init"
		>
			<detail-header-item slot="detail-header-item"
				:value="country"
			></detail-header-item>
			<detail-header-item slot="detail-header-item"
				:value="site_name"
			></detail-header-item>
			<detail-header-item slot="detail-header-item"
				:value="joined_when"
			></detail-header-item>

		</detail-view>

		<h5 v-if="profile">{{ item_container_heading }}</h5>
		<item-cards-container
			:container_name="item_container_heading"
			:items="items"
			:item_id_fieldname="item_id_fieldname"
			:on_click="go_to_item_details_page"
		>
		</item-cards-container>
	</div>
</template>

<script>
export default {
	name: 'seller-page',
	data() {
		return {
			page_name: frappe.get_route()[1],
			seller_company: frappe.get_route()[2],

			init: true,

			profile: null,
			items:[],
			item_id_fieldname: 'name',

			title: null,
			image: null,
			sections: [],

			country: '',
			site_name: '',
			joined_when: '',
		};
	},
	created() {
		this.get_seller_profile_and_items();
	},
	computed: {
		item_container_heading() {
			return __('Items by ' + this.seller_company);
		}
	},
	methods: {
		get_seller_profile_and_items() {
			hub.call(
				'get_hub_seller_page_info',
				{ company: this.seller_company }
			).then(data => {
				this.init = false;
				this.profile = data.profile;
				this.items = data.items;

				const profile = this.profile;

				this.title = profile.company;

				this.country = __(profile.country);
				this.site_name = __(profile.site_name);
				this.joined_when = __(`Joined ${comment_when(profile.creation)}`);

				this.image = profile.logo;
				this.sections = [
					{
						title: __('About the Company'),
						content: profile.company_description
							? __(profile.company_description)
							: __('No description')
					}
				];
			});
		},

		go_to_item_details_page(hub_item_name) {
			frappe.set_route(`marketplace/item/${hub_item_name}`);
		}
	}
}
</script>

<style scoped></style>
