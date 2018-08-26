<template>
	<div
		class="marketplace-page"
		:data-page-name="page_name"
		v-if="init || profile"
	>

		<detail-view
			:title="title"
			:subtitles="subtitles"
			:image="image"
			:sections="sections"
			:show_skeleton="init"
		>
		</detail-view>
	</div>
</template>

<script>
import DetailView from '../components/DetailView.vue';

export default {
	name: 'profile-page',
	components: {
		DetailView
	},
	data() {
		return {
			page_name: frappe.get_route()[1],

			init: true,

			profile: null,
			title: null,
			subtitles: [],
			image: null,
			sections: []
		};
	},
	created() {
		this.get_profile();
	},
	methods: {
		get_profile() {
			hub.call(
				'get_hub_seller_profile',
				{ hub_seller: hub.settings.company_email }
			).then(profile => {
				this.init = false;

				this.profile = profile;
				this.title = profile.company;
				this.subtitles = [
					__(profile.country),
					__(profile.site_name),
					__(`Joined ${comment_when(profile.creation)}`)
				];
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
