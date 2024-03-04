# voe-dl
A Python downloader for voe.sx videos

# Warning

**Please use always the newest Version, because these suckers at voe change their site from time to time
to make it harder for us to download via script!**
**Currently working Version is v1.1.1**

# Usage
1. Download the latest Release
2. add the executable to PATH (just search for how to do it if you don't know)
3. use the:

### Single File Downloader
```
voe-dl [URL]
voe-dl -u [URL]
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
voe-dl -l [File_Name]
```
  It will download the links one after another
  
# Output
The Output Video Files will be saved in the folder you execute the script

# Help
execute
```
voe-dl -h
```
for help directly from the script
