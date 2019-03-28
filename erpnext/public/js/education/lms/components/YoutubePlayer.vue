<template>
	<div class="embed-responsive embed-responsive-16by9">
        <iframe class="embed-responsive-item yvideo" :src="'https://www.youtube.com/embed/' + videoID + '?version=3&enablejsapi=1'" allowfullscreen></iframe>
    </div>
</template>
<script type="text/javascript">
	export default {
		name: 'YoutubePlayer',
		props: ['url'],
		data() {
			return {
				videoID: ''
			}
		},
		watch: {
			url() {
				this.videoID = this.getVideoID(this.url)
			}
		},
		methods: {
			getVideoID(link) {
				if (!Array.prototype.last){
					Array.prototype.last = function(){
						return this[this.length - 1];
					};
				};
				if (link.includes('v=')){
					return link.split('v=')[1].split('&')[0]
				}
				else if (link.includes('youtu.be')) {
					return link.split('/').last().split('?')[0]
				}
		    }
		}
	};
</script>