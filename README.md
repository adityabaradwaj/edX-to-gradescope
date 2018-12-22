# edX-to-gradescope

A script for converting edX's online assignment format to Gradescope online assignment format.


Some notes:
Also it looks like you do not even need to put in the hashes for the different assignments. I think I figured out the tree to search through the pre-existing structure. You first look at the course.xml to get the url_name, you then go to the course/*url_name*.xml file to read the current homeworks. From there you go into the chapter folder for each chapter hash you have. The chapter hash file gives you the sequential hash file which has a folder containing another file. That file will then have the verticals which you then need.