<template>
	<div class="hub-item-container">
		<div class="row visible-xs">
			<div class="col-xs-12 margin-bottom">
				<button class="btn btn-xs btn-default" data-route="marketplace/home">{{ back_to_home_text }}</button>
			</div>
		</div>

		<div v-if="show_skeleton" class="row margin-bottom">
			<div class="col-md-3">
				<div class="hub-item-skeleton-image"></div>
			</div>
			<div class="col-md-6">
				<h2 class="hub-skeleton" style="width: 75%;">Name</h2>
				<div class="text-muted">
					<p class="hub-skeleton" style="width: 35%;">Details</p>
					<p class="hub-skeleton" style="width: 50%;">Ratings</p>
				</div>
				<hr>
				<div class="hub-item-description">
					<p class="hub-skeleton">Desc</p>
					<p class="hub-skeleton" style="width: 85%;">Desc</p>
				</div>
			</div>
		</div>

		<div v-else>
			<div class="row margin-bottom">
				<div class="col-md-3">
					<div class="hub-item-image">
						<img :src="image">
					</div>
				</div>
				<div class="col-md-6">
					<h2>{{ title }}</h2>
					<div class="text-muted">
						<p v-for="subtitle in subtitles"
							:key="subtitle"
							v-html="subtitle"
						>
						</p>
					</div>

				</div>
			</div>
			<div v-for="section in sections" class="row hub-item-description margin-bottom"
				:key="section.title"
			>
				<h6 class="col-md-12 margin-top">
					<b class="text-muted">{{ section.title }}</b>
				</h6>
				<p class="col-md-12" v-html="section.content">
				</p>
			</div>
		</div>

	</div>
</template>

<script>

export default {
	name: 'detail-view',
	props: ['title', 'subtitles', 'image', 'sections', 'show_skeleton'],
	data() {
		return {
			back_to_home_text: __('Back to Home')
		}
	},
	computed: {}
}
</script>

<style lang="less" scoped>
</style>
