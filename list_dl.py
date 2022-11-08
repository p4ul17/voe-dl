import os
import dl as dl

os.chdir(os.path.dirname(os.path.abspath(__file__)))

curLink = 0
lines = open("links.txt").readlines()
for link in lines:
    curLink +=1
    print("Download %s / "%curLink + str(len(lines)))
    link = link.replace("\n","")
    print("echo Link: %s"%link)
    dl.download(link)