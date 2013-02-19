PyExt2
======
An [Ext2 filesystem](http://wikipedia.org/wiki/Ext2) interface written entirely in Python.


License
-------
This software is released under the BSD license. See the file 'LICENSE' for details.


Requirements
------------
The ext2 module requires Python 2.6 or 2.7. Using the module requires access to a filesystem image formatted to the ext2 filesystem.


Usage
-----
To run the module, use the diskbot script:

`diskbot ext2_image_file.img -s`

will open a shell for interacting with the filesystem image.

`diskbot -h`

will display usage options for the script.


Acknowledgement
---------------
Special thanks to Dave Poirier for making available the [ext2-doc project](http://www.nongnu.org/ext2-doc/). It has been an enormous help in developing this project.
