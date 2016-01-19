<h1>Nested BOM Structure</h1>

**Question:** Our manufacturing process involves producing sub-assembly items before final product. How should we manage BOM master in this scenario?

**Answer:** You should create BOM for item in the order of their production. Let's consider an example to understand this better.

If Computer manufacturer assembles Hard Disk and DVD Drive (sub-assemblies) themselves, they should first create BOM for Hard Disk and DVD Drive. After that BOM for Computer will be created, which is finished and saleable item. BOM of computer will have&nbsp;
Hard Disk and DVD Drive (sub-assemblies) will be selected as raw-material items in it. BOM ID will be fetched for the respective sub-assembly item.


<img src="{{docs_base_url}}/assets/img/articles/Screen Shot 2015-04-02 at 3.58.19 pm.png">

<br>Following is how the structure of nested BOM will look:
<br>
<br><b>Computer (FG Item)</b>
<br><b>---</b> Mother Board
<br><b>---</b> SMTP
<br><b>---</b> Accessories and wires
<br><b>---</b>  <i>Hard Disk (sub-assembly)</i>
<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ------ Item A
<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ------ Item B
<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ------ Item C
<br><b>---</b>  <i>DVD Drive (sub-assembly)</i>
<br>&nbsp;&nbsp;&nbsp; &nbsp; ------ Item X
<br>&nbsp; &nbsp; &nbsp; ------ Item Y
<br>&nbsp;&nbsp; &nbsp;&nbsp; ------ Item Z
<br>


<!-- markdown -->