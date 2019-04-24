<template>
	<div class="modal" id="videoModal" tabindex="-1" role="dialog">
		<div class="modal-dialog" role="document">
			<div class="modal-content">
			<div class="modal-header">
				<h5 class="modal-title">{{ title }}</h5>
				<button type="button" class="close" data-dismiss="modal" aria-label="Close">
				<span id="close_modal" aria-hidden="true" @click="stopVideo()">&times;</span>
				</button>
			</div>
			<div class="modal-body">
				<youtube-player :url="video"/>
			</div>
			</div>
		</div>
	</div>
</template>
<script type="text/javascript">
import YoutubePlayer from './YoutubePlayer.vue'

export default {
	name: 'VideoModal',
	props: ['title', 'video'],
	components: {
		YoutubePlayer
	},
	methods: {
		stopVideo() {
			$('.yvideo').each(function() {
  				this.contentWindow.postMessage('{"event":"command","func":"stopVideo","args":""}', '*')
			});
		}
	}
};
</script>