$(function () {
    setTimeout(function () {
        $(".later").fadeIn();
    }, 1000);
});

$(document).ready(function () {
    
    var $videoSrc;
    // Gets the video src from the data-src on each button
    $('.video-btn').click(function () {
        $videoSrc = $(this).attr("data-src");
        console.log($videoSrc);
    });
    console.log($videoSrc);


    // when the modal is opened autoplay it  
    $('#myModal').on('shown.bs.modal', function (e) {

        // set the video src to autoplay and not to show related video. Youtube related video is like a box of chocolates... you never know what you're gonna get
        $("#ytplayer").attr('src', "https://www.youtube.com/embed/" + $videoSrc + "?autoplay=0");
    })
    // stop playing the youtube video when I close the modal
    $('#myModal').on('hide.bs.modal', function (e) {
        // a poor man's stop video
        $("#ytplayer").attr('src', $videoSrc);
    })
    // document ready  
});