
cur_frm.cscript.load_taxes=function(doc,cdt,cdn){if(doc.customer)return;$c_obj([doc],'load_default_taxes','',function(r,rt){refresh_field('other_charges');});}
cur_frm.add_fetch('company','default_currency','currency');cur_frm.cscript.customer=function(doc,cdt,cdn){if(doc.customer){if(!doc.company){msgprint("Please select company to proceed");doc.customer='';refresh_field('customer');}else{var callback=function(r,rt){cur_frm.refresh();}
$c_obj(make_doclist(doc.doctype,doc.name),'get_customer_details','',callback);}}}
cur_frm.cscript.TerritoryHelp=function(doc,dt,dn){var call_back=function(){var sb_obj=new SalesBrowser();sb_obj.set_val('Territory');}
loadpage('Sales Browser',call_back);}
cur_frm.cscript.CGHelp=function(doc,dt,dn){var call_back=function(){var sb_obj=new SalesBrowser();sb_obj.set_val('Customer Group');}
loadpage('Sales Browser',call_back);}
cur_frm.cscript.currency=function(doc,cdt,cdn){cur_frm.cscript.price_list_name(doc,cdt,cdn);}
cur_frm.cscript.price_list_name=function(doc,cdt,cdn){var fname=cur_frm.cscript.fname;if(doc.price_list_name&&doc.currency){$c_obj(make_doclist(doc.doctype,doc.name),'get_adj_percent','',function(r,rt){refresh_field(fname);var doc=locals[cdt][cdn];cur_frm.cscript.recalc(doc,3);});}}
cur_frm.cscript.conversion_rate=function(doc,cdt,cdn){cur_frm.cscript.recalc(doc,3);}
cur_frm.fields_dict[cur_frm.cscript.fname].grid.get_field("item_code").get_query=function(doc,cdt,cdn){if(doc.order_type=='Maintenance')
return'SELECT tabItem.name,tabItem.item_name,tabItem.description FROM tabItem WHERE tabItem.is_service_item="Yes" AND tabItem.docstatus != 2 AND (ifnull(`tabItem`.`end_of_life`,"") = "" OR `tabItem`.`end_of_life` > NOW() OR `tabItem`.`end_of_life`="0000-00-00") AND tabItem.%(key)s LIKE "%s" LIMIT 50';else
return'SELECT tabItem.name,tabItem.item_name,tabItem.description FROM tabItem WHERE tabItem.is_sales_item="Yes" AND tabItem.docstatus != 2 AND (ifnull(`tabItem`.`end_of_life`,"") = "" OR `tabItem`.`end_of_life` > NOW() OR `tabItem`.`end_of_life`="0000-00-00") AND tabItem.%(key)s LIKE "%s" LIMIT 50';}
cur_frm.cscript.item_code=function(doc,cdt,cdn){var fname=cur_frm.cscript.fname;var d=locals[cdt][cdn];if(d.item_code){if(!doc.company){msgprint("Please select company to proceed");d.item_code='';refresh_field('item_code',d.name,fname);}else{var callback=function(r,rt){cur_frm.cscript.recalc(doc,1);}
get_server_fields('get_item_details',d.item_code,fname,doc,cdt,cdn,1,callback);}}
if(cur_frm.cscript.custom_item_code){cur_frm.cscript.custom_item_code(doc,cdt,cdn);}}
cur_frm.cscript.qty=function(doc,cdt,cdn){cur_frm.cscript.recalc(doc,1);}
cur_frm.cscript.adj_rate=function(doc,cdt,cdn){cur_frm.cscript.recalc(doc,1);}
cur_frm.cscript.ref_rate=function(doc,cdt,cdn){var d=locals[cdt][cdn];set_multiple(cur_frm.cscript.tname,d.name,{'export_rate':flt(d.ref_rate)*(100-flt(d.adj_rate))/100},cur_frm.cscript.fname);cur_frm.cscript.recalc(doc,3);}
cur_frm.cscript.basic_rate=function(doc,cdt,cdn){var fname=cur_frm.cscript.fname;var d=locals[cdt][cdn];;if(!d.qty)
{d.qty=1;refresh_field('qty',d.name,fname);}
cur_frm.cscript.recalc(doc,2);}
cur_frm.cscript.export_rate=function(doc,cdt,cdn){cur_frm.cscript.recalc(doc,3);}
cur_frm.fields_dict.charge.get_query=function(doc){return'SELECT DISTINCT `tabOther Charges`.name FROM `tabOther Charges` WHERE `tabOther Charges`.company = "'+doc.company+'" AND `tabOther Charges`.company is not NULL AND `tabOther Charges`.docstatus != 2 AND `tabOther Charges`.%(key)s LIKE "%s" ORDER BY `tabOther Charges`.name LIMIT 50';}
cur_frm.cscript['Get Charges']=function(doc,cdt,cdn){$c_obj(make_doclist(doc.doctype,doc.name),'get_other_charges','',function(r,rt){cur_frm.cscript['Calculate Charges'](doc,cdt,cdn);});}
cur_frm.cscript.recalc=function(doc,n){if(!n)n=0;doc=locals[doc.doctype][doc.name];var tname=cur_frm.cscript.tname;var fname=cur_frm.cscript.fname;var sales_team=cur_frm.cscript.sales_team_fname;var other_fname=cur_frm.cscript.other_fname;if(!flt(doc.conversion_rate)){doc.conversion_rate=1;refresh_field('conversion_rate');}
if(n>0)cur_frm.cscript.update_fname_table(doc,tname,fname,n);if(flt(doc.net_total)>0){var cl=getchildren('RV Tax Detail',doc.name,other_fname,doc.doctype);for(var i=0;i<cl.length;i++){cl[i].total_tax_amount=0;cl[i].total_amount=0;cl[i].tax_amount=0;cl[i].total=0;cl[i].item_wise_tax_detail="";if(in_list(['On Previous Row Amount','On Previous Row Total'],cl[i].charge_type)&&!cl[i].row_id){alert("Please Enter Row on which amount needs to be calculated for row : "+cl[i].idx);validated=false;}}
cur_frm.cscript.calc_other_charges(doc,tname,fname,other_fname);}
cur_frm.cscript.calc_doc_values(doc,cdt,cdn,tname,fname,other_fname);cl=getchildren('Sales Team',doc.name,sales_team);for(var i=0;i<cl.length;i++){if(cl[i].allocated_percentage){cl[i].allocated_amount=flt(flt(doc.net_total)*flt(cl[i].allocated_percentage)/100);refresh_field('allocated_amount',cl[i].name,sales_team);}}
doc.in_words='';doc.in_words_export='';refresh_many(['total_discount_rate','total_discount','net_total','total_commission','grand_total','rounded_total','grand_total_export','rounded_total_export','in_words','in_words_export','other_charges','other_charges_total']);if(cur_frm.cscript.custom_recalc)cur_frm.cscript.custom_recalc(doc);}
cur_frm.cscript.calc_doc_values=function(doc,cdt,cdn,tname,fname,other_fname){doc=locals[doc.doctype][doc.name];var net_total=0;var other_charges_total=0;var cl=getchildren(tname,doc.name,fname);for(var i=0;i<cl.length;i++){net_total+=flt(cl[i].amount);}
var d=getchildren('RV Tax Detail',doc.name,other_fname,doc.doctype);for(var j=0;j<d.length;j++){other_charges_total+=flt(d[j].amount);}
doc.net_total=flt(net_total);doc.other_charges_total=flt(other_charges_total);doc.grand_total=flt(flt(net_total)+flt(other_charges_total));doc.rounded_total=Math.round(doc.grand_total);doc.grand_total_export=flt(flt(doc.grand_total)/flt(doc.conversion_rate));doc.rounded_total_export=Math.round(doc.grand_total_export);doc.total_commission=flt(flt(net_total)*flt(doc.commission_rate)/100);}
cur_frm.cscript.calc_other_charges=function(doc,tname,fname,other_fname){doc=locals[doc.doctype][doc.name];cur_frm.fields_dict['Other Charges Calculation'].disp_area.innerHTML='<b style="padding: 8px 0px;">Calculation Details for Other Charges:</b>';var cl=getchildren(tname,doc.name,fname);var tax=getchildren('RV Tax Detail',doc.name,other_fname,doc.doctype);var otc=make_table(cur_frm.fields_dict['Other Charges Calculation'].disp_area,cl.length+1,tax.length+1,'90%',[],{border:'1px solid #AAA',padding:'2px'});$y(otc,{marginTop:'8px'});var tax_desc={};var tax_desc_rates=[];var net_total=0;for(var i=0;i<cl.length;i++){net_total+=flt(flt(cl[i].qty)*flt(cl[i].basic_rate));var prev_total=flt(cl[i].amount);if(cl[i].item_tax_rate)
var check_tax=eval('var a='+cl[i].item_tax_rate+';a');$td(otc,i+1,0).innerHTML=cl[i].item_code?cl[i].item_code:cl[i].description;var tax=getchildren('RV Tax Detail',doc.name,other_fname,doc.doctype);var total=net_total;for(var t=0;t<tax.length;t++){var account=tax[t].account_head;$td(otc,0,t+1).innerHTML=account?account:'';if(cl[i].item_tax_rate&&check_tax[account]!=null){rate=flt(check_tax[account]);}
else
rate=flt(tax[t].rate);var tax_amount=cur_frm.cscript.check_charge_type_and_get_tax_amount(doc,tax,t,cl[i],rate);item_wise_tax_detail=cur_frm.cscript.get_item_wise_tax_detail(doc,rate,cl,i,tax,t);if(tax[t].charge_type!="Actual")tax[t].item_wise_tax_detail+=item_wise_tax_detail;tax[t].total_amount=flt(tax_amount.toFixed(2));tax[t].total_tax_amount=flt(prev_total.toFixed(2));tax[t].tax_amount+=flt(tax_amount.toFixed(2));var total_amount=flt(tax[t].tax_amount);total_tax_amount=flt(tax[t].total_tax_amount)+flt(total_amount);set_multiple('RV Tax Detail',tax[t].name,{'item_wise_tax_detail':tax[t].item_wise_tax_detail,'amount':total_amount,'total':flt(total)+flt(tax[t].tax_amount)},other_fname);prev_total+=flt(tax[t].total_amount);total+=flt(tax[t].tax_amount);if(tax[t].charge_type=='Actual')
$td(otc,i+1,t+1).innerHTML=fmt_money(tax[t].total_amount);else
$td(otc,i+1,t+1).innerHTML='('+fmt_money(rate)+'%) '+fmt_money(tax[t].total_amount);}}}
cur_frm.cscript.check_charge_type_and_get_tax_amount=function(doc,tax,t,cl,rate,print_amt){doc=locals[doc.doctype][doc.name];if(!print_amt)print_amt=0;var tax_amount=0;if(tax[t].charge_type=='Actual'){var value=flt(tax[t].rate)/flt(doc.net_total);return tax_amount=flt(value)*flt(cl.amount);}
else if(tax[t].charge_type=='On Net Total'){if(flt(print_amt)==1){doc.excise_rate=flt(rate);doc.total_excise_rate+=flt(rate);refresh_field('excise_rate');refresh_field('total_excise_rate');return}
return tax_amount=(flt(rate)*flt(cl.amount)/100);}
else if(tax[t].charge_type=='On Previous Row Amount'){if(flt(print_amt)==1){doc.total_excise_rate+=flt(flt(doc.excise_rate)*0.01*flt(rate));refresh_field('total_excise_rate');return}
var row_no=(tax[t].row_id).toString();var row=(row_no).split("+");for(var r=0;r<row.length;r++){var id=cint(row[r].replace(/^\s+|\s+$/g,""));tax_amount+=(flt(rate)*flt(tax[id-1].total_amount)/100);}
var row_id=row_no.indexOf("/");if(row_id!=-1){rate='';var row=(row_no).split("/");if(row.length>2)alert("You cannot enter more than 2 nos. for division");var id1=cint(row[0].replace(/^\s+|\s+$/g,""));var id2=cint(row[1].replace(/^\s+|\s+$/g,""));tax_amount=flt(tax[id1-1].total_amount)/flt(tax[id2-1].total_amount);}
return tax_amount}
else if(tax[t].charge_type=='On Previous Row Total'){if(flt(print_amt)==1){doc.sales_tax_rate+=flt(rate);refresh_field('sales_tax_rate');return}
var row=cint(tax[t].row_id);return tax_amount=flt(rate)*(flt(tax[row-1].total_tax_amount)+flt(tax[row-1].total_amount))/100;}}
cur_frm.cscript.update_fname_table=function(doc,tname,fname,n){doc=locals[doc.doctype][doc.name]
var net_total=0
var cl=getchildren(tname,doc.name,fname);for(var i=0;i<cl.length;i++){if(n==1){if(flt(cl[i].ref_rate)>0)
set_multiple(tname,cl[i].name,{'export_rate':flt(flt(cl[i].ref_rate)*(100-flt(cl[i].adj_rate))/100)},fname);set_multiple(tname,cl[i].name,{'export_amount':flt(flt(cl[i].qty)*flt(cl[i].export_rate)),'basic_rate':flt(flt(cl[i].export_rate)*flt(doc.conversion_rate)),'amount':flt((flt(cl[i].export_rate)*flt(doc.conversion_rate))*flt(cl[i].qty))},fname);}
else if(n==2){if(flt(cl[i].ref_rate)>0)
set_multiple(tname,cl[i].name,{'adj_rate':100-flt(flt(cl[i].basic_rate)*100/(flt(cl[i].ref_rate)*flt(doc.conversion_rate)))},fname);set_multiple(tname,cl[i].name,{'amount':flt(flt(cl[i].qty)*flt(cl[i].basic_rate)),'export_rate':flt(flt(cl[i].basic_rate)/flt(doc.conversion_rate)),'export_amount':flt((flt(cl[i].basic_rate)/flt(doc.conversion_rate))*flt(cl[i].qty))},fname);}
else if(n==3){set_multiple(tname,cl[i].name,{'basic_rate':flt(flt(cl[i].export_rate)*flt(doc.conversion_rate))},fname);set_multiple(tname,cl[i].name,{'amount':flt(flt(cl[i].basic_rate)*flt(cl[i].qty)),'export_amount':flt(flt(cl[i].export_rate)*flt(cl[i].qty))},fname);if(cl[i].ref_rate>0)
set_multiple(tname,cl[i].name,{'adj_rate':100-flt(flt(cl[i].export_rate)*100/flt(cl[i].ref_rate)),'base_ref_rate':flt(flt(cl[i].ref_rate)*flt(doc.conversion_rate))},fname);}
net_total+=flt(flt(cl[i].qty)*flt(cl[i].basic_rate));}
doc.net_total=net_total;refresh_field('net_total');}
cur_frm.cscript.get_item_wise_tax_detail=function(doc,rate,cl,i,tax,t){doc=locals[doc.doctype][doc.name];var detail='';detail=cl[i].item_code+" : "+cstr(rate)+NEWLINE;return detail;}
cur_frm.cscript['Re-Calculate Values']=function(doc,cdt,cdn){cur_frm.cscript['Calculate Charges'](doc,cdt,cdn);}
cur_frm.cscript['Calculate Charges']=function(doc,cdt,cdn){var other_fname=cur_frm.cscript.other_fname;var cl=getchildren('RV Tax Detail',doc.name,other_fname,doc.doctype);for(var i=0;i<cl.length;i++){cl[i].total_tax_amount=0;cl[i].total_amount=0;cl[i].tax_amount=0;cl[i].total=0;if(in_list(['On Previous Row Amount','On Previous Row Total'],cl[i].charge_type)&&!cl[i].row_id){alert("Please Enter Row on which amount needs to be calculated for row : "+cl[i].idx);validated=false;}}
cur_frm.cscript.recalc(doc,1);}
cur_frm.cscript.sales_partner=function(doc,cdt,cdn){if(doc.sales_partner){get_server_fields('get_comm_rate',doc.sales_partner,'',doc,cdt,cdn,1);}}
cur_frm.cscript.commission_rate=function(doc,cdt,cdn){if(doc.commission_rate>100){alert("Commision rate cannot be greater than 100.");doc.total_commission=0;doc.commission_rate=0;}
else
doc.total_commission=doc.net_total*doc.commission_rate/100;refresh_many(['total_commission','commission_rate']);}
cur_frm.cscript.total_commission=function(doc,cdt,cdn){if(doc.net_total){if(doc.net_total<doc.total_commission){alert("Total commission cannot be greater than net total.");doc.total_commission=0;doc.commission_rate=0;}
else
doc.commission_rate=doc.total_commission*100/doc.net_total;refresh_many(['total_commission','commission_rate']);}}
cur_frm.cscript.allocated_percentage=function(doc,cdt,cdn){var fname=cur_frm.cscript.sales_team_fname;var d=locals[cdt][cdn];if(d.allocated_percentage){d.allocated_amount=flt(flt(doc.net_total)*flt(d.allocated_percentage)/100);refresh_field('allocated_amount',d.name,fname);}}
cur_frm.cscript.validate=function(doc,cdt,cdn){cur_frm.cscript.validate_items(doc);var cl=getchildren('Other Charges',doc.name,'other_charges');for(var i=0;i<cl.length;i++){if(!cl[i].amount){alert("Please Enter Amount in Row no. "+cl[i].idx+" in Other Charges table");validated=false;}}
cur_frm.cscript['Calculate Charges'](doc,cdt,cdn);if(cur_frm.cscript.calc_adjustment_amount)cur_frm.cscript.calc_adjustment_amount(doc);}
cur_frm.cscript.validate_items=function(doc){var cl=getchildren(cur_frm.cscript.tname,doc.name,cur_frm.cscript.fname);if(!cl.length){alert("Please enter Items for "+doc.doctype);validated=false;}}