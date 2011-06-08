var hr_set_tips = function() {
  $c_obj('Module Tip Control', 'get_tip', 'hr', function(r,rt) { 
    if(r.message) {
      $(parent.tip_area).html('<b>Tip: </b>' + r.message).css('display','block');
    }
  } );
}

hr_set_tips();