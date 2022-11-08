# voe-dl
A Python downloader for voe.sx videos


# Usage
1. Download the Repo
2. install dependencies via pip
   > bs4  (BeatifulSoup) 
   
   > wget
3. use the:

### Single File Downloader
    python dl.py [URL]
   
  whereas [URL] is the Link to the voe site\
  just downloads the link you specify
   
### Multiple File Downloader
  Put your links in [links.txt], one at each line\
  example:
```
https://voe.sx//xxxxxxx
https://voe.sx//yyyyyyy
https://voe.sx//zzzzzzz
```
  execute
```
python list_dl.py
```
  It will download the links one after another
  
# Output
The Output Video Files will be saved in the /output folder
