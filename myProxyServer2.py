'''
To figure out the request format
Usage: Use Firefox Safe Mode to deactivate autoFill HTTP CONNECT method
add version control
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
            self.listen(self.max_conn)
        except KeyboardInterrupt:
            print(self.getTimeStamp()+' KeyboardInterrupt')
            self.write_log(self.getTimeStamp()+' KeyboardInterrupt')
            time.sleep(.5)
        finally:
            print(self.getTimeStamp()+' Stopping Server..')
            self.write_log(self.getTimeStamp()+' Stopping Server..\n\n')
            sys.exit()

    def listen(self, max_conn):
        try:
            self.listen_socket = socket.socket(self.address_family,self.socket_type)
            self.listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.listen_socket.bind(self.server_address)
            self.listen_socket.listen(self.max_conn)
        except:
            print(self.getTimeStamp() + "   Error: Cannot start listening...")
            self.write_log(self.getTimeStamp() + "   Error: Cannot start listening...")
            sys.exit(1)

        while True:
            try:
                conn, addr = self.listen_socket.accept()
                start_new_thread(self.read_request, (conn,addr))
            except Exception as e:
                print(self.getTimeStamp() + '   Error: Fail to accept client...'+str(e))
                self.write_log(self.getTimeStamp() + '   Error: Fail to accept client...'+str(e))
                sys.exit(1)
    # a new thread
    def read_request(self, conn, addr):
        buffer_size = 65536
        try:
            request = conn.recv(buffer_size)
            header = request.splitlines()
            # debug
            print('the header\n',header)
            self.write_log('\n'.join(line for line in header))
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
                    
            # debug
            print('     webserver: {}   port: {}'.format(webserver, port))
            #self.write_log('{}##{}'.format(webserver, port))
            self.write_log('     webserver: {}   port: {}'.format(webserver, port))

            # handle request 
            # IS HTTPS CONNECT REQUEST
            if method == b'CONNECT':
                print(self.getTimeStamp() + '   HTTPS CONNECT Request')
                self.write_log(self.getTimeStamp() + '   HTTPS CONNECT Request')
                self.https_proxy(webserver, port, conn, header)
            # IS HTTP GET REQUEST
            elif method == b'GET':
                print(self.getTimeStamp()+'     HTTP GET Request')
                self.write_log(self.getTimeStamp()+'     HTTP GET Request')
                self.http_proxy(webserver, port, conn, header)
            else:
                print(self.getTimeStamp()+'    Unexpected Request method')
                self.write_log(self.getTimeStamp()+'    Unexpected Request method')
                sys.exit(1)
        except Exception as e:
            print(self.getTimeStamp()+'     Error: cannot read quest ' + str(e)+'\n')
            self.write_log(self.getTimeStamp()+'     Error: cannot read quest '+ str(e)+'\n')
            return
            

    # We can use HTTP/1.0 to send data back to the client
    # HTTP/1.1 will require a 'Host: ' key and persistent connection
    # Second thought
    # Do HTTPS requests expect a HTTPS response?

    # Generate HTTP response client <=??=> proxy_server
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
    
    def generate_request_GET(self, header):
        h = ''
        for line in header:
            if not line.split(': ')[0] == 'Connection':
                h = h + line + '\r\n'
        h += 'Connection: close\r\n'
        h += '\r\n' # there is a blank line
        print(self.getTimeStamp()+'    HTTP request\n' + h)
        self.write_log(self.getTimeStamp()+'    HTTP request\n' + h)

    # do not handle https for now
    def https_proxy(self,webserver, port, conn, header):
        response_content = 'hello from https proxy!\r\n'
        http_headers = self.generate_header_lines(status=200, length=len(response_content))
        # debug
        response = 'HTTP/1.1 200 OK\r\nHost: myProxyServer.com\r\n\r\nHello\r\n'
        conn.sendall(response)
        conn.close()
        #print(response)

    def handle_http_request(self, webserver, header):
        dir = os.path.join(os.getcwd(), 'cache')
        if not os.path.exists(dir):
            os.mkdir('cache')
        dir_cache = os.path.join(dir, webserver.replace('.','__'))
        if not os.path.exists(dir_cache):
            os.mkdir(dir_cache)
        ## should use a make_dir function
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        http_request = self.generate_request_GET(header)
        s.connect((webserver, 80))
        s.sendall(http_request)
        result = s.recv(65536)
        return result

        

    
    def http_proxy(self,webserver, port, conn, header):
        request_file = self.handle_http_request(webserver, header)
        #print(self.getTimeStamp() + '   get response from the server')
        #self.write_log(self.getTimeStamp() + '   get response from the server'+request_file)



        response_content = 'hello from http proxy!\r\n'
        http_headers = self.generate_header_lines(status=200, length=len(response_content))
        
        #conn.sendall(http_headers.encode('utf-8'))
        #time.sleep(1)
        #conn.sendall(response_content)
        
        # debug All tested and work
        #conn.sendall('HTTP/1.0 200 OK\r\n\r\nHello\r\n')
        #http_response = http_headers+response_content
        http_response = http_headers+self.client_page.format(msg='Hello world! from HTTP proxy!')
        #http_response = http_headers+self.client_error_page.format(status_code=404,msg='Not Found!')
        conn.sendall(http_response.encode('utf-8')) # I remember HTTP or SMTP use UTF-8

        #conn.sendall(request_file.encode('utf-8'))

        conn.close()




if __name__ == '__main__':
    if len(sys.argv) <= 1:
        sys.exit('Usage: python ProxyServer.py [port]')
    server_address = ('', int(sys.argv[1]))
    server = Server(server_address)
    server.serve_forever()