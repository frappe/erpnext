// Global dictionary of next steps for doctypes
// ============================================
pscript.tip_doc_dict = {'Quotation':['Sales Order'], 'Sales Order':['Delivery Note', 'Sales Invoice'], 'Delivery Note':['Sales Invoice'], 'Receivable Voucher':['Bank Voucher'], 'Indent':['Purchase Order'], 'Purchase Order':['Purchase Invoice'], 'Payable Voucher':['Bank Voucher'], 'Purchase Receipt':['Purchase Invoice'], 'Enquiry':['Quotation'], 'Lead':['Enquiry', 'Customer']};

pscript.master_doctype_lst =['Authorization Rule','Bank','Batch','Branch','Brand','Business Letter','Business Letter Template','Business Letter Type','Campaign','City','Company','Contact','Cost Center','Country','Customer','Customer Group','Deduction Type','Department','Designation','Earning Type','Employee','Employment Type','Expense Type','File Group','Fiscal Year','Grade','Holiday List','Industry Type','Item','Item Group','KRA Template','Landed Cost Master','Lead','Leave Type', 'Manage Account', 'Mode of Payment','Order Lost Reason','Other Charges','Period','Price List','Print Heading','Project','Purchase Other Charges','Purpose of Service','Sales BOM','Sales Partner','Sales Person','Serial No','State','Supplier','Supplier Type','TDS Category','Term','Territory','Ticket Category','UOM','Warehouse','Warehouse Type','Workflow Rule','Workstation'];

// Set tips depending on conditions
// ================================
cur_frm.cscript.get_tips = function(doc, cdt, cdn){
  
  var next_step_list = pscript.tip_doc_dict[cur_frm.doctype];
  // from is shown in print format
  
  
  if(!cur_frm.editable && cur_frm.doctype!='Enquiry' && pscript.master_doctype_lst.join().indexOf(cur_frm.doctype)<0){
    cur_frm.set_tip("Click on the <div style='font-weight:bold; display:inline'>Edit</div> button above to edit this " + get_doctype_label(cur_frm.doctype) + ".");
  }
  
  
  // form is not in print format
  if(cur_frm.editable){
    // new doc
    if(pscript.master_doctype_lst.join().indexOf(cur_frm.doctype)>=0){
      if(doc.__islocal)
        cur_frm.set_tip("To create " + get_doctype_label(cur_frm.doctype) + " please start by entering all the mandatory fields (marked <div style='color:Red; display:inline'> Red</div>).<br><br> You can then save this form by clicking on the <div style='font-weight:bold; display:inline'>Save</div> button in the above toolbar.");
      else
        cur_frm.set_tip("You have saved this " + get_doctype_label(cur_frm.doctype) + ".");
    }
    else {
      if(doc.__islocal){
        if(doc.status=='Cancelled' || doc.amended_from)
          cur_frm.set_tip("You can now make changes in this " + get_doctype_label(cur_frm.doctype) + " and save it by clicking on the <div style='font-weight:bold; display:inline'>Save</div> button in the above toolbar.");
        else 
          cur_frm.set_tip("To create " + get_doctype_label(cur_frm.doctype) + " please start by entering all the mandatory fields (marked <div style='color:Red; display:inline'> Red</div>).<br><br> You can then save this form by clicking on the <div style='font-weight:bold; display:inline'>Save</div> button in the above toolbar.");
      }
      
      // doc exists
      else if(!doc.__islocal){
        // execute when doc is saved
        //if(doc.docstatus==0 && cur_frm.doctype!='Enquiry' && cur_frm.doctype!='Lead')
        if(doc.docstatus==0 && cur_frm.doctype!='Lead')
          cur_frm.set_tip("You have saved your " + get_doctype_label(cur_frm.doctype) + ". You can make this draft permanent by clicking on <div style='font-weight:bold; display:inline'>Submit</div> button above.");
          
        // execute if doc has only save permission
        //else if(doc.docstatus==0 && (cur_frm.doctype=='Enquiry' || cur_frm.doctype=='Lead')){
        else if(doc.docstatus==0 && (cur_frm.doctype=='Lead')){
          cur_frm.set_tip("You have saved this " + get_doctype_label(cur_frm.doctype) + ".");
          for(var i=0; i<next_step_list.length; i++){
            if(i==0)  cur_frm.append_tip("To proceed select the <div style='font-weight:bold; display:inline'>Next Steps</div> tab below and click the button to create a " + next_step_list[i] +".");
            else  cur_frm.append_tip("You can also create a " + next_step_list[i] + " against this " + get_doctype_label(cur_frm.doctype) + ".");
          }
        }
        // execute if doc is submitted
        else if(doc.docstatus==1){
          cur_frm.set_tip("You have submitted this " + get_doctype_label(cur_frm.doctype) + ".");
          for(var i=0; i<next_step_list.length; i++){
            if(i==0)  cur_frm.append_tip("To proceed select the Next Steps tab below and click the button to create a " + next_step_list[i] +".");
            else  cur_frm.append_tip("You can also create a " + next_step_list[i] + " against this " + get_doctype_label(cur_frm.doctype) + ".");
          }
          cur_frm.append_tip("(To amend this "+ get_doctype_label(cur_frm.doctype) + " click on the <div style='font-weight:bold; display:inline'>Cancel</div> button above.)");
        }
        
        // execute when doc is amended
        else if(doc.docstatus==2){
          cur_frm.set_tip("To make this " + get_doctype_label(cur_frm.doctype) + " editable click on the <div style='font-weight:bold; display:inline'>Amend</div> button above.");
        }
      }
    }
  }
}

// Executes when doc is edit status of doc is changed
// ==================================================
cur_frm.cscript.edit_status_changed = function(doc, cdt, cdn){
  cur_frm.cscript.get_tips();
}


// Executes when module page is loaded
pscript.show_module_stats = function(parent, module)
{
  this.parent = parent;
  this.module = module;
  alert(profile.can_read)
  //msgprint(parent, 1);
  msgprint(module, 1);
}