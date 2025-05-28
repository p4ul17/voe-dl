from setuptools import setup

with open("requirements.txt") as f:
    install_requires = f.read().splitlines()

setup(
  name="voe-dl",
  version="1.5.1",
  author="p4ul17",
  description="A Python downloader for voe.sx videos",
  install_requires=install_requires,
  scripts=[
    "dl.py",
  ],
  entry_points={
    #"console_scripts": ["voe-dl=dl:main"]
  },
)
