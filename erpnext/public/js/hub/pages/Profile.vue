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
	</div>
</template>

<script>
export default {
	name: 'profile-page',
	data() {
		return {
			page_name: frappe.get_route()[1],

			init: true,

			profile: null,
			title: null,
			image: null,
			sections: [],

			country: '',
			site_name: '',
			joined_when: '',
		};
	},
	created() {
		this.get_profile();
	},
	methods: {
		get_profile() {
			hub.call(
				'get_hub_seller_profile',
				{ hub_seller: hub.settings.hub_seller_name }
			).then(profile => {
				this.init = false;

				this.profile = profile;
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
		}
	}
}
</script>

<style scoped></style>
