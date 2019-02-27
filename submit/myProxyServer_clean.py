'''
> Implementation of a HTTP proxy server
> Tested on Molliza Firefox
> How to test:
> 0. Disable url autoFill (inorder to disable HTTPS redirect)
     FireFox -> type 'about:config' in url bar:
             -> search 'autoFill' -> change the Value of 'browser.urlbar.autoFill' to 'False'
             -> search 'preload' -> change the Value of 'network.stricttransportsecurity.preloadlist' to 'False'
             -> reopen FireFox
             -> open a New Private Window
> 1. open Firefox -> Options -> Connection Settings
> 2. Choose 'Manual proxy settings' and set:
     HTTP Proxy: localhost   Port: 8080 (or the port you choose to run this server)
> 3. run the ProxyServer.py on the port (e.g. 8080)
> 4. In the url bar, type in the url like:
     e.g. http://www.example.com
     The web page will show and be cached locally.
> 5. In order to test the cache feature, you may need to clean the brower history and caches
     FirFox -> histor -> Clear All History -> In 'Time range to clear' choose everything
     -> check all options from the 'History' (including 'Cache') -> Clear Now
> 6. Type in the url again to test the cache feature
     The cache file is stored in ~/cache/HOSTNAME/*.cache
     And you can check the log file in ~/log/log.txt to check whether cache works
     The result is also printed out on the terminal

> features: handle HTTP GET request
            cache objects from web pages including html and images
            multi-thread support

            Error handling
            Cache verification and replacement


'''


import socket
import sys, os
import datetime, time
from thread import start_new_thread


class Server:
    address_family = socket.AF_INET
    socket_type = socket.SOCK_STREAM
    max_conn = 5

    client_page = """
    <html>
    <body>
    <p>{msg}<p>
    </body>
    </html>
    """
    client_error_page = """
    <html>
    <body>
    <h>{status_code}</h>
    <h>{msg}</h>
    </body>
    </html>
    """

    def __init__(self, server_address):
        self.server_address = server_address
        self.host = server_address[0]
        self.port = int(server_address[1])
        

    # Function to get timestamp
    def getTimeStamp(self):
        return "[" + str(datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')) + ']'
    
    # Function to write logs
    def write_log(self, msg):
        dir = os.getcwd()
        dir = os.path.join(dir,'log')
        if not os.path.exists(dir):
            os.mkdir('log')
        with open('log/log.txt', 'a+') as file:
            file.write(msg)
            file.write('\n')

    def serve_forever(self):
        try:
            print(self.getTimeStamp()+' Start listening')
            self.write_log(self.getTimeStamp()+' Start listening')
            # ready to accept new connections from the clients
            self.listen(self.max_conn)
        except KeyboardInterrupt:
            print(self.getTimeStamp()+' KeyboardInterrupt')
            self.write_log(self.getTimeStamp()+' KeyboardInterrupt')
            time.sleep(.5)
        finally:
            print(self.getTimeStamp()+' Stopping Server..')
            self.write_log(self.getTimeStamp()+' Stopping Server..\n\n')
            sys.exit()

    # create a listen socket
    # bind it to the port
    # accept a connection
    def listen(self, max_conn):
        try:
            self.listen_socket = socket.socket(self.address_family,self.socket_type)
            self.listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.listen_socket.bind(self.server_address)
            self.listen_socket.listen(self.max_conn)
        except:
            print(self.getTimeStamp() + " Error: Cannot start listening...")
            self.write_log(self.getTimeStamp() + " Error: Cannot start listening...")
            sys.exit(1)

        while True:
            try:
                # for every new connection, we start a new thread to handle it
                # enable the proxy server to handle multiple requests
                # at the same time (multi-thread feature)
                conn, addr = self.listen_socket.accept()
                start_new_thread(self.read_request, (conn,addr))
            except Exception as e:
                print(self.getTimeStamp() + ' Error: Fail to accept client... Error: '+str(e))
                self.write_log(self.getTimeStamp() + ' Error: Fail to accept client... Error: '+str(e))
                sys.exit(1)
    
    # a new thread, handle one request
    def read_request(self, conn, addr):
        buffer_size = 65536
        try:
            request = conn.recv(buffer_size)
            header = request.splitlines()
            # print and log the request message from the client
            print(self.getTimeStamp() + ' Request from a client\n' +'\n'.join(line for line in header))
            self.write_log(self.getTimeStamp() + ' Request from a client\n' +'\n'.join(line for line in header))
            # parse the request line (the first line of the request)
            # method: e.g. GET, CONNECT ..   path: the url version:HTTP/1.1, HTTP/1.0 ...
            method, path, version = header[0].split(' ')
            # There are different formats of path to parse
            # get domain and port from the path
            index_host = path.find(b'://')
            if index_host == -1:
                temp = path
            else:
                temp = path[index_host+3:] # first strip out http:// or https://
            
            #index_port = path.find(b':')
            index_port = temp.find(b':')
            #index_webserver = path.find(b'/')
            index_webserver = temp.find(b'/')
            if index_webserver == -1:
                index_webserver = len(temp) # to get full string (substr of len(temp))

            # if there is no port in the path, use port 80 and HTTP (GET)
            # otherwise, use the port in the header e.g. 443 and HTTPS(CONNECT)
            webserver = ''
            port = -1
            # Try to parse the webserver(host) and port
            # ignore request from the system
            if (index_port == -1) or (index_webserver < index_port):
                port = 80
                webserver = temp[:index_webserver]
            else:
                port = int((temp[index_port+1:])[:index_webserver-index_port-1])
                webserver = temp[:index_port]
                    
            # parser result
            print(self.getTimeStamp() + ' a requst to Addr: {}   Port: {}'.format(webserver, port))
            #self.write_log('{}##{}'.format(webserver, port))
            self.write_log(self.getTimeStamp() + ' a requst to Addr: {}   Port: {}'.format(webserver, port))

            # handle request 
            # Is HTTPS CONNECT request
            # the browser wants the proxy to forward the connection and create the direct https tunnel to the remote server
            # we do not handle HTTPS CONNCT method in this version
            # but simply print out a message and log there is a CONNECT request from the client
            if method == b'CONNECT':
                print(self.getTimeStamp() + ' HTTPS CONNECT Request')
                self.write_log(self.getTimeStamp() + ' HTTPS CONNECT Request')
                # ignore CONNECT request
                #self.https_proxy(webserver, port, conn, header)
                return
            # Is HTTP GET request
            # handle HTTP GET request
            elif method == b'GET':
                print(self.getTimeStamp()+' HTTP GET Request')
                self.write_log(self.getTimeStamp()+' HTTP GET Request')
                # begin to handle HTTP GET request here
                self.http_proxy(webserver, port, conn, header)
            else:
                # invalid method, log and exit
                print(self.getTimeStamp()+' Unexpected Request method')
                self.write_log(self.getTimeStamp()+' Unexpected Request method')
                sys.exit(1)
        except Exception as e:
            print(self.getTimeStamp()+' Error: cannot read quest Error: ' + str(e)+'\n')
            self.write_log(self.getTimeStamp()+' Error: cannot read quest Error: '+ str(e)+'\n')
            return
            

    # generate header for HTTP response from the proxy server
    def generate_header_lines(self, status, length):
        h = ''
        if status == 200:
            h = 'HTTP/1.0 200 OK\r\n'
            h += 'Server: myProxyServer\r\n'
        elif status == 404:
            h = 'HTTP/1.0 404 Not Found\r\n'
            h += 'Date: ' + time.strftime('%a, %d %b %Y %H:%M:%S', time.localtime()) + '\r\n'
            h += 'Server: myProxyServer\r\n'
        h += 'Content-Length: ' + str(length) + '\r\n'
        h += 'Connection: close\r\n'
        h += '\r\n' # the end of the header and the start of the data
        return h

    # do not handle https for now
    # this function is implemented just for degugging
    def https_proxy(self,webserver, port, conn, header):
        response_content = 'hello from https proxy!\r\n'
        http_headers = self.generate_header_lines(status=200, length=len(response_content))
        # debug
        response = 'HTTP/1.1 200 OK\r\nHost: myProxyServer.com\r\n\r\nHello\r\n'
        conn.sendall(response)
        conn.close()
        #print(response)

    # to receive full message 
    def recv_all(self, conn):
        buffer_size = 1024
        response = ''
        while True:
            r = conn.recv(buffer_size)
            if len(r) == 0:
                break
            response += r
        return response
    
    def check_cache(self, webserver, port,conn, header):
        # check if there is a cache file
        # if exists : send it back (#check if is up-to-date)
        # not exists: remote request, send it back, cache (cache after send for efficiency)
        dir = os.path.join(os.getcwd(), 'cache')
        if not os.path.exists(dir):
            os.mkdir('cache')
        dir = os.path.join(dir, webserver)
        if not os.path.exists(dir):
            os.mkdir(dir)
        
        filename = header[0].split(' ')[1]
        filename = filename.replace('/','_')
        filename = filename.replace('?','~')
        filename = filename.replace(':','_~_')
        filename += '.cache'
        
        
        print('FILENAME',filename)
        cache_dir = os.path.join(dir, filename)
        # cache_status
        # Ture: cached      False: not cached
        cache_status = os.path.exists(cache_dir)
        # no cache found, retrieve remotely
        if not cache_status:
            # cache and return
            print(self.getTimeStamp() + ' No cache file found')
            self.write_log(self.getTimeStamp() + ' No cache file found')
            h = ''
            for line in header[:-1]: # the last line is a black line
                if (not 'Connection' in line) and (not 'Upgrade-Insecure-Requests' in line):
                    h  += line + '\r\n'
            h += 'Connection: close\r\n\r\n'
            #print('Request-Server-From-Proxy\n')
            #print(h)
            print(self.getTimeStamp() + 'Request file from the remote server\nRequsting...\nRequest Message\n'+h)
            #self.write_log('Request-Server-From-Proxy\n'+h)
            self.write_log(self.getTimeStamp() + 'Request file from the remote server\nRequsting...\nRequest Message\n'+h)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((webserver, 80))
            s.sendall(h)
            #re = s.recv(65536)
            re = self.recv_all(s)
            # change to wb+
            with open(cache_dir,'wb+') as f: 
                f.write(re)
            return re
        else:
            # Hit a cache
            # return the cache file
            re = ''
            print(self.getTimeStamp() + ' Hit Cache!' + filename)
            self.write_log(self.getTimeStamp() + ' Hit Cache!' + filename)
            with open(cache_dir,'rb') as f:
                re = f.read()
            return re
            


            

    # handle HTTP GET
    def http_proxy(self,webserver, port, conn, header):
        re = self.check_cache(webserver, port, conn, header)
        print(self.getTimeStamp() + ' Get the requested file\n####\n' + re)
        self.write_log(self.getTimeStamp() + ' Get the requested file\n####\n' + re)
        # send it back to the client
        conn.sendall(re)
        conn.close()

        




if __name__ == '__main__':
    if len(sys.argv) <= 1:
        sys.exit('Usage: python ProxyServer.py [port]')
    server_address = ('', int(sys.argv[1]))
    server = Server(server_address)
    server.serve_forever()