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
						<base-image :src="image" :alt="title" />
					</div>
				</div>
				<div class="col-md-8" style='padding-left: 30px;'>
					<h2>{{ title }}</h2>
					<div class="text-muted">
						<slot name="detail-header-item"></slot>
					</div>
				</div>

				<div v-if="menu_items && menu_items.length" class="col-md-1">
					<div class="dropdown pull-right hub-item-dropdown">
						<a class="dropdown-toggle btn btn-xs btn-default" data-toggle="dropdown">
							<span class="caret"></span>
						</a>
						<ul class="dropdown-menu dropdown-right" role="menu">
							<li v-for="menu_item in menu_items"
								v-if="menu_item.condition"
								:key="menu_item.label"
							>
								<a @click="menu_item.action">{{ menu_item.label }}</a>
							</li>
						</ul>
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
	props: ['title', 'image', 'sections', 'show_skeleton', 'menu_items'],
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
