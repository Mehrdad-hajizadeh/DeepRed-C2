"""
27.2.2025
- add probability to select exfil or not + reduce the number of selecting videos as it make pcap large
----
9.2.2025
- This code create random action list to be executed during the bot-c2 communications
- We see the communication as a disctionry of different actions. even underlaying configurations are also consider as one action to be executed.
- there are termination limit which when exceed it will close the connections 
see, project_note to get updated 
"""

from typing import List
import psutil, socket, yaml, random, os
import pandas as pd


class config_generator:
    def __init__(self, config_file_addr, **kwargs):
        self.kwargs= kwargs
        with open(config_file_addr) as stream:
            try:
                self.config = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        self.rce_list_generator()
        #add arbitrary probability to select if we add exfil or not to the action list 
        threshold = .9 # 40% probability to select exfil
        flag = False
        rnd= random.random()
        if threshold:
            flag= rnd < threshold
        if flag:
            self.exfil_list_generator()
        else:
            self.flattened_exfil_list= []
        if self.kwargs:
            self.add_underlaying_config()
    def flatten_list(self, nested_list):
        flat_list = []
        for item in nested_list:
            if isinstance(item, list):
                flat_list.extend(self.flatten_list(item))
            else:
                flat_list.append(item)
        return flat_list
    def rce_list_generator(self):    
        rce_rnd_action_list= []
        discovery_action_list= random.choices(list(self.config["rce"].keys()), k=random.randint(1,len(list(self.config["rce"].keys()))))
        for action in discovery_action_list:
            rce_rnd_action_list.append(random.choices(self.config["rce"][action], k=random.randint(1,len(self.config["rce"][action]))))
        self.flattened_rce_list = self.flatten_list(rce_rnd_action_list)
    def exfil_list_generator(self):
        sample_data_for_exfil_path = self.config["exfil_data_address"] # path to the sample data for exfiltration configs/bot_activity.yaml
        
        # Collect all file paths except readme.txt
        all_files = []
        for root, dirs, files in os.walk(sample_data_for_exfil_path):
            for file in files:
                if file.lower() != "readme.txt":
                    all_files.append(os.path.join(root, file))
        # Randomly select between 1 and len(all_files) files
        if all_files:
            num_files = random.randint(1, len(all_files))
            selected_files = random.sample(all_files, num_files)
        else:
            selected_files = []


        self.flattened_exfil_list = self.flatten_list(selected_files)
    def add_underlaying_config(self):
        if self.kwargs: # expilicitly determin the params in the 
            self.underlaying_config = {key: value for key, value in self.kwargs.items()}
        #else: # if not then use it from config file itseld
            #self.underlaying_config = 


    def config_maker (self):
        """
        Generates a shuffled configuration dictionary by combining RCE (Remote Command Execution) and exfiltration items.
        The method processes two lists: `flattened_rce_list` and `flattened_exfil_list`, assigning each item a unique key
        (e.g., 'rce_0', 'exfil_0'). If additional keyword arguments (`kwargs`) are present, they are merged into the configuration
        along with an underlying configuration dictionary (`underlaying_config`). The resulting dictionary is shuffled to randomize
        the order of its items before being returned.

        Returns:
            dict: A shuffled dictionary containing RCE, exfiltration, and optionally additional configuration items.
        """
        rce = {}
        exfil = {}
        for i, item in enumerate(self.flattened_rce_list):
            rce[f"rce_{i}"] = item
        if len(self.flattened_exfil_list) > 0:
            for j, item in enumerate(self.flattened_exfil_list):
                exfil[f"exfil_{j}"]= item
        if self.kwargs:
            dict_ = (rce | exfil | self.underlaying_config) # add ++kwargs to action list
        else: 
            dict_ = (rce | exfil )
        combined = list(dict_.items())
        random.shuffle(combined)
        shuffled_dic = dict (combined)
        return shuffled_dic
"""
# test 
from pathlib import Path

# Get the directory of the currently running script
script_dir = Path(__file__).parent.parent

# Construct the path to conf.yaml from the script directory
conf_path = script_dir / "configs" / "bot_activity.yaml"
a = config_generator(f"{conf_path}")
print(a.config_maker())
"""
