This folder contains sample files that simulate data hosted on a victim machine. 
These files are targeted for exfiltration by the Command and Control (C2) server during communication.

You can add arbitrary files to this directory—either directly in the current folder, in subfolders, or at the root level. 
The code recursively scans this folder and randomly selects files for exfiltration.

To specify the path to the exfiltration data folder, edit the configs/bot_activity.yaml file.