PyExt2
======
An [ext2 filesystem](http://wikipedia.org/wiki/Ext2) interface written entirely in Python. A live demo of the project can be seen online at [extbot.com](http://extbot.com).

Features:

* Supports variable block sizes
* Read/write/move/delete files and directories
* Create hard and symbolic links
* Create new filesystem images from scratch


License
-------
This software is released under the BSD license. See the file 'LICENSE' for details.


Requirements
------------
Requires Python 2.6 or 2.7. Using the module requires access to a filesystem image formatted to the ext2 filesystem.


Usage
-----
To run the module, use the diskbot script.

The command:

`diskbot ext2_image_file.img -s`

will open a shell for interacting with the filesystem image and the command:

`diskbot -h`

will display usage options for the script.


Acknowledgement
---------------
Thanks to Dave Poirier for making available the [ext2-doc project](http://www.nongnu.org/ext2-doc/). It has been a great help in developing this project.
