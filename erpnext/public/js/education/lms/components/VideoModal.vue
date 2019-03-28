<template>
  <div class="modal" id="videoModal" tabindex="-1" role="dialog">
  <div class="modal-dialog" role="document">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title">{{ title }}</h5>
        <button type="button" class="close" data-dismiss="modal" aria-label="Close">
          <span aria-hidden="true">&times;</span>
        </button>
      </div>
      <div class="modal-body">
        <div class="embed-responsive embed-responsive-16by9">
            <iframe class="embed-responsive-item" :src="'https://www.youtube.com/embed/' + videoID"></iframe>
        </div>
      </div>
    </div>
  </div>
</div>
</template>
<script type="text/javascript">
export default {
  name: 'VideoModal',
  props: ['title', 'video'],
  computed: {
      videoID() {
          if (!Array.prototype.last){
              Array.prototype.last = function(){
                  return this[this.length - 1];
              };
          };
          if (this.video.includes('v=')){
              return this.video.split('v=')[1].split('&')[0]
          }
          else if (this.video.includes('youtu.be')) {
              return this.video.split('/').last().split('?')[0]
          }
      }
  }
};
</script>