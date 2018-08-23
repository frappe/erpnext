<template>
	<div class="col-md-3 col-sm-4 col-xs-6 hub-card-container">
		<div class="hub-card is_local">
			<div class="hub-card-header flex">
				<div>
					<div class="hub-card-title ellipsis bold">{{ title }}</div>
					<div class="hub-card-subtitle ellipsis text-muted" v-html='subtitle'></div>
				</div>
			</div>
			<div class="hub-card-body">
				<img class="hub-card-image" :src="item.image"/>
				<div class="hub-card-overlay">
					<div class="hub-card-overlay-body">
						<div class="hub-card-overlay-button" style="right: 15px; bottom: 15px;">
							<button class="btn btn-default zoom-view">
								<i class="octicon octicon-pencil text-muted"></i>
							</button>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script>

export default {
	name: 'item-card',
	props: ['item', 'is_local'],
	computed: {
		title() {
			return this.item.item_name
		},
		subtitle() {
			return comment_when(this.item.creation);
		}
	}
}
</script>

<style scoped></style>
