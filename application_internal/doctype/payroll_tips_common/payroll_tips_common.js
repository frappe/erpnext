// Global dictionary of next steps for doctypes
// ============================================
pscript.payroll_tip_dict = {'Employee':['Payroll Rule', 'Salary Structure'], 'Salary Structure':['IT Checklist', 'Salary Slip']};

// Set tips depending on conditions
// ================================
cur_frm.cscript.get_tips = function(doc, cdt, cdn)
{
  
  var next_step_list = pscript.payroll_tip_dict[cur_frm.doctype];
  
  // from is shown in print format
  if(!cur_frm.editable){
    cur_frm.set_tip("Click on the <div style='font-weight:bold; display:inline'>Edit</div> button above to edit this " + cur_frm.doctype + ".");
  }
  
  // form is not in print format
  if(cur_frm.editable){
    // new doc
    if(doc.__islocal){
      if(doc.status=='Cancelled' || doc.amended_from)
        cur_frm.set_tip("You can now make changes in this " + cur_frm.doctype + " and save it by clicking on the <div style='font-weight:bold; display:inline'>Save</div> button in the above toolbar.");
      
      // doc is completely new
      else{
        // For Salary Slip
        if(cur_frm.doctype=='Salary Slip'){
          cur_frm.set_tip("To create " + cur_frm.doctype + " please enter all the details and save it by clicking on the <div style='font-weight:bold; display:inline'>Save</div> button in the above toolbar.");
          cur_frm.append_tip("To calculate earnings and deductions click on <div style='font-weight:bold; display:inline'>Process Payroll</div> button after saving the form");
        }
        // For IT Checklist
        else if(cur_frm.doctype=='IT Checklist'){
          cur_frm.set_tip("To create " + cur_frm.doctype + " please enter all the details and click on <div style='font-weight:bold; display:inline'>Done</div> button below to fetch all the details in the remaining tabs.");
          cur_frm.append_tip("To calculate taxes, please enter the actual amount in all the tables in the remaining tabs and click on <div style='font-weight:bold; display:inline'>Calculate</div> button in the <div style='font-weight:bold; display:inline'>Total Taxable Income</div> tab.");
        }
        // For Others
        else
          cur_frm.set_tip("To create " + cur_frm.doctype + " please start by entering all the mandatory fields(marked <div style='color:Red; display:inline'> Red</div>).<br><br> You can then save this form by clicking on the <div style='font-weight:bold; display:inline'>Save</div> button in the above toolbar.");
      }  
    }
    
    // doc exists
    else if(!doc.__islocal){
      // execute when doc is saved
      if(doc.docstatus==0 && cur_frm.doctype=='Salary Slip'){
        cur_frm.set_tip("You have saved your " + cur_frm.doctype + ". To calculate earnings and deductions click on <div style='font-weight:bold; display:inline'>Process Payroll</div> button below.");
        cur_frm.append_tip("You can make this draft permanent by clicking on <div style='font-weight:bold; display:inline'>Submit</div> button above.")
      }
      
      // execute if doc is submitted
      else if(doc.docstatus==1 && cur_frm.doctype=='Salary Slip'){
        cur_frm.set_tip("You have submitted this " + cur_frm.doctype + ".");
        cur_frm.append_tip("(To make changes in this "+ cur_frm.doctype + " click on the <div style='font-weight:bold; display:inline'>Cancel</div> button above.)");
      }
     
      // execute if doc has only save permission
      else if(doc.docstatus==0 && (cur_frm.doctype=='IT Checklist' || cur_frm.doctype=='Salary Structure' || cur_frm.doctype=='Employee')){
        cur_frm.set_tip("You have saved this " + cur_frm.doctype + ".");
               
        for(var i=0; i<next_step_list.length; i++){
          if(i==0)  cur_frm.append_tip("To proceed select the Next Steps tab below and click the button to create  " + next_step_list[i] +".");
          else  cur_frm.append_tip("You can also create a " + next_step_list[i] + " for this " + cur_frm.doctype + ".");
        }
      }
      
      // execute when doc is amended
      else if(doc.docstatus==2){
        cur_frm.set_tip("To make this " + cur_frm.doctype + " editable click on the <div style='font-weight:bold; display:inline'>Amend</div> button above.");
      }
    }
  }
}

// Executes when doc is edit status of doc is changed
// ==================================================
cur_frm.cscript.edit_status_changed = function(doc, cdt, cdn){
  cur_frm.cscript.get_tips();
}