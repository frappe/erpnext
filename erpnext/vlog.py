import datetime
def vwrite(contenttowrite):
    target = open("verpnextlogfile.txt", 'a+')
    target.write("\n==========================="+str(datetime.datetime.now())+"===========================\n")
    target.write("\n"+str(contenttowrite)+"\n")
    target.close()
