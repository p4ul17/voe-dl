# coding=utf-8
import sys, os, glob
import re
import requests
import json
import wget
from bs4 import BeautifulSoup
from yt_dlp import YoutubeDL
import base64 # import base64

def main():
    args = sys.argv #saving the cli arguments into args

    try:
        args[1]     #try if args has a value at index 1
    except IndexError:
        print("Please use a parameter. Use -h for Help") #if not, tells the user to specify an argument
        quit()

    if args[1] == "-h":     #if the first user argument is "-h" call the help function
        help()
    elif args[1] == "-u":   #if the first user argument is "-u" call the download function
        URL = args[2]
        download(URL)
    elif args[1] == "-l":   #if the first user argument is "-l" call the list_dl (list download) function
        doc = args[2]
        list_dl(doc)
    else:
        URL = args[1]       #if the first user argument is the <URL> call the download function
        download(URL)

def help():
    print("Version v1.2.4")
    print("")
    print("______________")
    print("Arguments:")
    print("-h shows this help")
    print("-u <URL> downloads the <URL> you specify")
    print("-l <doc> opens the <doc> you specify and downloads every URL line after line")
    print("<URL> just the URL as Argument works the same as with -u Argument")
    print("______________")
    print("")
    print("Credits to @NikOverflow, @cuitrlal and @cybersnash on GitHub for contributing")

def list_dl(doc):
    curLink = 0
    lines = open(doc).readlines()       #reads the lines of the given document and store them in the list "lines"
    for link in lines:                  #calls the download function for every link in the document
        curLink +=1
        print("Download %s / "%curLink + str(len(lines)))
        link = link.replace("\n","")
        print("echo Link: %s"%link)
        download(link)

def download(URL):
    URL = str(URL)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "de,en-US;q=0.7,en;q=0.3",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Priority": "u=1"
    }
    html_page = requests.get(URL, headers=headers)

    soup = BeautifulSoup(html_page.content, 'html.parser')
    if html_page.text.startswith("<script>"):
        START = "window.location.href = '"
        L = len(START)
        i0 = html_page.text.find(START)
        i1 = html_page.text.find("'",i0+L)
        url = html_page.text[i0+L:i1]
        return download(url)

    name = soup.find('title').string
    name = name.replace(" ","_")
    print("Name of file: " + name)


    sources_find = soup.find_all(string = re.compile("var sources")) #searching for the script tag containing the link to the mp4
    sources_find = str(sources_find)
    #slice_start = sources_find.index("const sources")
    slice_start = sources_find.index("var sources")
    source = sources_find[slice_start:] #cutting everything before 'var sources' in the script tag
    slice_end = source.index(";")
    source = source[:slice_end] #cutting everything after ';' in the remaining String to make it ready for the JSON parser

    source = source.replace("var sources = ","")    #
    source = source.replace("\'","\"")                #Making the JSON valid
    source = source.replace("\\n","")                 #
    source = source.replace("\\","")                  #

    strToReplace = ","
    replacementStr = ""
    source = replacementStr.join(source.rsplit(strToReplace, 1)) #complicated but needed replacement of the last comma in the source String to make it JSON valid

    source_json = json.loads(source) #parsing the JSON
    try:
        link = source_json["mp4"] #extracting the link to the mp4 file
        link = base64.b64decode(link)
        link = link.decode("utf-8")
        wget.download(link, out=f"{name}_SS.mp4") #downloading the file
    except KeyError:
        try:
            link = source_json["hls"]
            link = base64.b64decode(link)
            link = link.decode("utf-8")

            name = name +'_SS.mp4'

            ydl_opts = {'outtmpl' : name,}
            with YoutubeDL(ydl_opts) as ydl:
                try:
                    ydl.download(link)
                except Exception as e:
                    pass
            delpartfiles()

        except KeyError:
            print("Could not find downloadable URL. Voe might have change their site. Check that you are running the latest version of voe-dl, and if so file an issue on GitHub.")
            quit()

    print("\n")

def delpartfiles():
    path = os.getcwd()
    for file in glob.iglob(os.path.join(path, '*.part')):
        os.remove(file)

if __name__ == "__main__":
    main()
