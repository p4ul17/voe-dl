# voe-dl
A Python downloader for voe.sx videos


# Usage
1. Download the Repo
2. install dependencies via pip
   > bs4  (BeatifulSoup) 
   
   > wget
   
   > requests
3. use the:

### Single File Downloader
```
python dl.py [URL]
python dl.py -u [URL]
```
   
  whereas [URL] is the Link to the voe site\
  just downloads the link you specify
   
### Multiple File Downloader
  Put your links in [links.txt] or any other File, one at each line\
  example:
```
https://voe.sx//xxxxxxx
https://voe.sx//yyyyyyy
https://voe.sx//zzzzzzz
```
  execute
```
python dl.py -l [File_Name]
```
  It will download the links one after another
  
# Output
The Output Video Files will be saved in the folder you execute the script

# Help
execute
```
python dl.py -h
```
for help directly from the script
