# coding=utf-8
import sys, os, glob
import re
import requests
import json
import wget
from bs4 import BeautifulSoup
from yt_dlp import YoutubeDL
import base64 # import base64
import concurrent.futures # NEW: For Threading

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
        
        if len(args) > 3 and args[3] == "-w":   #if the second user argument is "-w" set the max_workers to the value of the third argument
            workers = int(args[4])
        else:
            workers = 4
            
        list_dl(doc, workers)
    else:
        URL = args[1]       #if the first user argument is the <URL> call the download function
        download(URL)

def help():
    print("Version v1.3.0")
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

def list_dl(doc, workers=4):
    """
    Reads lines from the specified doc file and downloads them in parallel.
    Lines starting with '#' and empty lines are ignored.
    """
    tmp_list = open(doc).readlines()
    fixed_list = [el for el in tmp_list if not el.startswith('#')]
    lines = [link.strip() for link in fixed_list if link.strip()]

    print(f"Downloading {len(lines)} files in parallel with {workers} threads...")

    # Execute parallel downloads with up to 4 threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_link = {executor.submit(download, link): link for link in lines}

        for i, future in enumerate(concurrent.futures.as_completed(future_to_link), start=1):
            link = future_to_link[future]
            print(f"Download {i} / {len(lines)}")
            print(f"echo Link: {link}")
            try:
                future.result()
            except Exception as e:
                print(f"[!] Error downloading {link}: {e}")

    # Remove .part files after all downloads are complete
    delpartfiles()

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
        i1 = html_page.text.find("'", i0 + L)
        url = html_page.text[i0 + L:i1]
        return download(url)

    name_find = soup.find('meta', attrs={"name": "og:title"})
    if name_find:
        name = name_find["content"]
        name = name.replace(" ", "_")
        print("Name of file: " + name)
    else:
        print("Could not find the name of the file in the meta tag. Using default name.")
        name = URL.split("/")[-1]  # Use the last part of the URL as the default file name
        print("Using default file name: " + name)

    sources_find = soup.find_all(string=re.compile("var sources"))  # Searching for the script tag containing the link to the mp4
    sources_find = str(sources_find)
    slice_start = sources_find.index("var sources")
    source = sources_find[slice_start:]  # Cutting everything before 'var sources' in the script tag
    slice_end = source.index(";")
    source = source[:slice_end]  # Cutting everything after ';' in the remaining string to make it ready for the JSON parser

    source = source.replace("var sources = ", "")
    source = source.replace("\'", "\"")  # Making the JSON valid
    source = source.replace("\\n", "")
    source = source.replace("\\", "")

    strToReplace = ","
    replacementStr = ""
    source = replacementStr.join(source.rsplit(strToReplace, 1))  # Replacement of the last comma in the source string to make it JSON valid

    source_json = json.loads(source)  # Parsing the JSON
    try:
        link = source_json["mp4"]  # Extracting the link to the mp4 file
        link = base64.b64decode(link)
        link = link.decode("utf-8")

        basename, ext = os.path.splitext(name)
        if not ext:
            ext = ".mp4"
        name = f"{basename}_SS{ext}"

        wget.download(link, out=name)
    except KeyError:
        try:
            link = source_json["hls"]
            link = base64.b64decode(link)
            link = link.decode("utf-8")

            basename, ext = os.path.splitext(name)
            if not ext:
                ext = ".mp4"
            name = f"{basename}_SS{ext}"

            ydl_opts = {'outtmpl': name}
            with YoutubeDL(ydl_opts) as ydl:
                try:
                    ydl.download([link])
                except Exception:
                    pass
        except KeyError:
            print("Could not find downloadable URL. The site might have changed. Ensure you're using the latest version of the script and file an issue on GitHub.")
            quit()

    print("\n")

def delpartfiles():
    path = os.getcwd()
    for file in glob.iglob(os.path.join(path, '*.part')):
        os.remove(file)

if __name__ == "__main__":
    main()
