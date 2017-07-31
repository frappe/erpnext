# Nested Bom Structure

#Nested BOM Structure

**Question:** Our manufacturing process involves producing sub-assembly items before final product. How should we manage BOM master in this scenario?

**Answer:** You should create BOM for item in the order of their production. BOM for the sub-assembly item should be created first. BOM for the Product Order item should be created last. Let's consider an example to understand this better.

A computer assembler is creating a BOM for PC. They also manufacture Hard Disk and DVD Drive themselve. They should first create BOM for Hard Disk and DVD Drive. After that BOM for the PC should be created.
 
BOM of PC will have all the raw-material items selected in it. Hard Disk and DVD Drive (sub-assemblies) will also be selected as raw-material items. For the sib-assembly items, respective BOM no. will be fetched as well.

<img alt="Nested BOM" class="screenshot" src="{{docs_base_url}}/assets/img/articles/nested-bom-1.png">

Following is how the structure of nested BOM will look:

<div class="well">
	
<b>-Personal Computer (FG Item)</b><br>
<b>---- Mother Board</b><br>
<b>---- SMTP</b><br>
<b>---- Accessories and wires</b><br>
<b>----<i>Hard Disk (sub-assembly)</i></b><br>
 ------- Item A<br>
 ------- Item B<br>
 ------- Item C<br>
<b>----<i>DVD Drive (sub-assembly)</i></b><br>
 ------- Item X<br>
 ------- Item Y<br>
 ------- Item Z

</div>



<!-- markdown -->