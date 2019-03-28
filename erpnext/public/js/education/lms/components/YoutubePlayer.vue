<template>
	<div class="embed-responsive embed-responsive-16by9">
        <iframe class="embed-responsive-item yvideo" :src="'https://www.youtube.com/embed/' + videoID + '?version=3&enablejsapi=1'" allowfullscreen></iframe>
    </div>
</template>
<script type="text/javascript">
	export default {
		name: 'YoutubePlayer',
		props: ['url', 'allowfullscreen'],
		computed: {
			videoID() {
				if (!Array.prototype.last){
					Array.prototype.last = function(){
						return this[this.length - 1];
					};
				};
				if (this.url.includes('v=')){
					return this.url.split('v=')[1].split('&')[0]
				}
				else if (this.url.includes('youtu.be')) {
					return this.url.split('/').last().split('?')[0]
				}
		    }
		}
	};
</script>