
/*
 *	erpnext/website/js/product_category.js
 */
erpnext.make_product_categories=function(wrapper){wrapper.category_list=new wn.ui.Listing({parent:$(wrapper).find('.more-categories').get(0),query:'select count(name) as items, item_group \
   from tabItem \
   where is_sales_item="Yes" and \
   ifnull(show_in_website, "No")="Yes" and \
   docstatus = 0 \
   group by item_group order by items desc',hide_refresh:true,render_row:function(parent,data){parent.innerHTML=repl('<a href="#!products/%(item_group)s">%(item_group)s</a> (%(items)s)',data);}});wrapper.category_list.run();console.log('product categories made');}