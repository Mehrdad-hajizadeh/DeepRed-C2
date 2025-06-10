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
import psutil, socket, yaml, random
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
        #add probability to select if we add exfil or not
        threshold = .2
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

        exfil_rnd_file_list =[]
        #file_rnd_list = random.choices(list(self.config["exfil"].keys()), k=random.randint(1,len(list(self.config["exfil"].keys()))))
        weights=[.3,.3,.1,.3]# video is less probability 
        file_rnd_list = random.choices(
            list(self.config["exfil"].keys()),
            weights=weights,
            k=random.randint(1, len(self.config["exfil"].keys()))
            )
        for item in file_rnd_list:
            exfil_rnd_file_list.append(random.choices(self.config["exfil"][item], k=random.randint(1,len(self.config["exfil"][item]))))
        self.flattened_exfil_list = self.flatten_list(exfil_rnd_file_list)
    def add_underlaying_config(self):
        if self.kwargs: # expilicitly determin the params in the 
            self.underlaying_config = {key: value for key, value in self.kwargs.items()}
        #else: # if not then use it from config file itseld
            #self.underlaying_config = 


    def config_maker (self):
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


# test 
from pathlib import Path

# Get the directory of the currently running script
script_dir = Path(__file__).parent.parent

# Construct the path to conf.yaml from the script directory
conf_path = script_dir / "configs" / 'config.yaml'
a = config_generator(f"{conf_path}", src2dst_packets=1000, dst2src_bytes= 5000)
print(a.config_maker())