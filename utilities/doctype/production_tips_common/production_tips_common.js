// Global dictionary of next steps for doctypes
// ============================================
pscript.tip_prod_dict = {'Production Order':['Material Transfer', 'Backflush']};


// Set tips depending on conditions
// ================================
cur_frm.cscript.get_tips = function(doc, cdt, cdn){
  var next_step_list = pscript.tip_prod_dict[cur_frm.doctype] ? pscript.tip_prod_dict[cur_frm.doctype] : 0;
  
  if(cur_frm.doctype!='Production Planning Tool'){
    // new doc
    if(doc.__islocal){
      if(doc.status=='Cancelled' || doc.amended_from)
        cur_frm.set_tip("You can now make changes in this " + cur_frm.doctype + " and save it by clicking on the <div style='font-weight:bold; display:inline'>Save</div> button in the above toolbar.");
      else{ 
        cur_frm.set_tip("To create " + cur_frm.doctype + " please start by entering all the mandatory fields (marked <div style='color:Red; display:inline'> Red</div>).");
        if(cur_frm.doctype=='Stock Entry') cur_frm.append_tip("If your purpose is Production Order, please go to <div style='font-weight:bold; display:inline'>Items</div> tab and click <div style='font-weight:bold; display:inline'>Get Items</div> to fetch the items.");
        cur_frm.append_tip("You can then save this form by clicking on the <div style='font-weight:bold; display:inline'>Save</div> button in the above toolbar.");
      }
    }
    
    // doc exists
    else if(!doc.__islocal){
      // execute when doc is saved
      if(doc.docstatus==0 && cur_frm.doctype!='Production Planning Tool')
        cur_frm.set_tip("You have saved your " + cur_frm.doctype + ". You can make this draft permanent by clicking on <div style='font-weight:bold; display:inline'>Submit</div> button above.");
        
      // execute if doc is submitted
      else if(doc.docstatus==1){
        cur_frm.set_tip("You have submitted this " + cur_frm.doctype + ".");
        for(var i=0; i<next_step_list.length; i++){
          if(i==0)  cur_frm.append_tip("To proceed select the <div style='font-weight:bold; display:inline'>Next Steps</div> tab below. To transfer raw materials to Finished Goods Warehouse click on <div style='font-weight:bold; display:inline'>" + next_step_list[i] +"</div>.");
          else  cur_frm.append_tip("To update the quantity of finished goods and raw materials in their respective warehouses click on <div style='font-weight:bold; display:inline'>" + next_step_list[i] + "</div>.");
        }
        cur_frm.append_tip("(To amend this "+ cur_frm.doctype + " click on the <div style='font-weight:bold; display:inline'>Cancel</div> button above.)");
      }
      
      // execute when doc is amended
      else if(doc.docstatus==2){
        cur_frm.set_tip("To make this " + cur_frm.doctype + " editable click on the <div style='font-weight:bold; display:inline'>Amend</div> button above.");
      }
    }
  }
}
  

// Execute if current doctype is Production Planning Tool
// ======================================================
cur_frm.cscript.get_PPT_tips = function(doc, cdt, cdn)
{
  cur_frm.set_tip('Welcome to Production Planning Wizard. This helps you to raise production order and see your raw material status as you plan your production.');
  cur_frm.append_tip("To start fetch all open Production Orders and Sales Orders by clicking on the <div style='font-weight:bold; display:inline'>Get Open Documents</div> button in the <div style='font-weight:bold; display:inline'>Against Document</div> tab below");
  
  cur_frm.cscript['Get Open Documents'] = function(doc, cdt, cdn){
    cur_frm.set_tip("To include the required orders in the Production Plan check mark the <div style='font-weight:bold; display:inline'>Include In Plan</div> cell below.");
    cur_frm.append_tip("Next you can go to the <div style='font-weight:bold; display:inline'>Items</div> tab and click on <div style='font-weight:bold; display:inline'>Get Items</div> button to fetch the items of the selected orders.");
  }
  
  cur_frm.cscript['Get Items'] = function(doc, cdt, cdn){
    cur_frm.set_tip("Now to raise a Production Order just click on <div style='font-weight:bold; display:inline'>Raise Production Ordre</div> button below the table.");
    cur_frm.append_tip("In order to see the Raw Material Report click on <div style='font-weight:bold; display:inline'>Get Raw Material Report</div> button below the table.");
  }
}


// Executes when doc is edit status of doc is changed
// ==================================================
cur_frm.cscript.edit_status_changed = function(doc, cdt, cdn){
  cur_frm.cscript.get_tips();
}
