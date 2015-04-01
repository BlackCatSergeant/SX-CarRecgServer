# -*- coding: cp936 -*-
'''
����ʶ�����ʹ��python2.7�汾��pulsar��ܡ�
���ش��룺
100: Success (ʶ��ɹ�)
101: Request Error (�������)
102: Recognise Error (ʶ�����)
103: Url Error (ͼƬurl·������)
104: Unknow Error (δ֪����)
105: Key Error (�û���Կ����)
106: Json Format Error (json��ʽ����)
107: Time Out (��ʱ)
108: Server Is Busy (����æ)
109: Recg Server Error (ʶ��������)
110: No Info Parameter (POSTȱ��info����)
'''
import urllib
import urlparse
import json
import threading
import Queue
import os
import logging
import logging.handlers
import time

try:
    from pulsar import MethodNotAllowed
except ImportError:  # pragma nocover
    import sys
    sys.path.append('../../')
    from pulsar import MethodNotAllowed

from pulsar.apps import wsgi
from pulsar.apps import socket 

import gl
from recg_thread import RecgThread
from iniconf import CarRecgSerIni
from sqlitedb import U_Sqlite
from help_func import HelpFunc

def initLogging(logFilename):
    """Init for logging"""
    path = os.path.split(logFilename)
    if os.path.isdir(path[0]):
        pass
    else:
        os.makedirs(path[0])
    logger = logging.getLogger('root')
    
    Rthandler = logging.handlers.RotatingFileHandler(logFilename, maxBytes=100*1024*1024,backupCount=5)
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(filename)s[line:%(lineno)d] [%(levelname)s] %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')
    Rthandler.setFormatter(formatter)
    logger.addHandler(Rthandler)

def version():
    return 'SX-CarRecgServer V0.4.0'

def hello(environ, start_response):
    '''The WSGI_ application handler which returns an iterable
    over the "Hello World!" message.'''
    #request_body = environ['wsgi.input']
    if environ['REQUEST_METHOD'] == 'POST' and environ['PATH_INFO']== '/recg':
        data = request_data(environ["wsgi.input"].read())
        status = '200 OK'
    elif environ['REQUEST_METHOD'] == 'POST' and environ['PATH_INFO']== '/state':
        data = state(environ["wsgi.input"].read())
        status = '200 OK'
    else:
        data = json.dumps({'carinfo':None,'msg':'Request Error','code':101})
        status = '400 Request Error'
        
    response_headers = [
        ('Content-type', 'text/plain'),
        ('Content-Length', str(len(data)))
    ]
    start_response(status, response_headers)
    return iter([data])

def server(description=None, **kwargs):
    '''Create the :class:`.WSGIServer` running :func:`hello`.'''
    description = description or 'RecgServer Application'

    return wsgi.WSGIServer(hello, name='RecgServer', description=description, **kwargs)

def state(wsgi_input):
    data = urllib.unquote_plus(wsgi_input)
    post_data = urlparse.parse_qs(data,True)
    
    user_info =  gl.KEYSDICT.get(post_data.get('key',[None])[0],None)
    #���KEY����ȷ���ش���
    if user_info is None:
        return json.dumps({'carinfo':None,'msg':'Key Error','code':105})
    else:
        return json.dumps({'carinfo':None,'msg':'State','code':120,'state':{'threads':gl.THREADS,'qsize':gl.P_SIZE},'user':user_info})

def request_data(wsgi_input):
    data = urllib.unquote_plus(wsgi_input)
    post_data = urlparse.parse_qs(data,True)
    #print post_data
    user_info =  gl.KEYSDICT.get(post_data.get('key',[None])[0],None)

    #���KEY����ȷ���ش���
    if user_info is None:
        return json.dumps({'carinfo':None,'msg':'Key Error','code':105})
    #JSON��ʽ����
    if post_data.get('info',None) == None:
        return json.dumps({'carinfo':None,'msg':'No Info Parameter','code':110})
    else:
        try:
            info = json.loads(post_data.get('info',[''])[0])
        except Exception as e:
            logger.error(e)
            return json.dumps({'carinfo':None,'msg':'Json Format Error','code':106})
    info['queue'] = Queue.Queue()

    priority = 30
    if gl.P_SIZE[priority] <= user_info['multiple']*gl.THREADS:
        priority = user_info['priority']
    elif gl.RECGQUE.qsize() > gl.MAXSIZE:
        return json.dumps({'carinfo':None,'msg':'Server Is Busy','code':108,'state':{'threads':gl.THREADS,'qsize':gl.P_SIZE},'user':user_info})
    else:
        priority += user_info['priority'] + 10
        
    gl.LOCK.acquire()
    gl.P_SIZE[priority] += 1
    gl.LOCK.release()
    gl.RECGQUE.put((priority,info,post_data.get('key',[None])[0]))
   
    try:
        recginfo = info['queue'].get(timeout=15)
        recginfo['state'] = {'threads':gl.THREADS,'qsize':gl.P_SIZE}
    except Queue.Empty:
        recginfo = {'carinfo':None,'msg':'Time Out','code':107,'state':{'threads':gl.THREADS,'qsize':gl.P_SIZE}}
    finally:
        gl.LOCK.acquire()
        gl.P_SIZE[priority] -= 1
        gl.LOCK.release()
        return json.dumps(recginfo)
        del info['queue']

class RecgServer:
    def __init__(self):
        self.crs = CarRecgSerIni()
        self.sysini = self.crs.get_sys_conf()
        self.centreini = self.crs.get_ser_centre_conf()
        self.sl = U_Sqlite()
        self.hf = HelpFunc()
        gl.RECGQUE = Queue.PriorityQueue()
        gl.LOCK = threading.Lock()

        #����ͼƬ�����ļ���
        self.file = 'img'
        if os.path.exists(self.file) == False:
            os.makedirs(self.file)
        #����ͼƬ��ȡ�ļ���
        self.file = 'cropimg'
        if os.path.exists(self.file) == False:
            os.makedirs(self.file)

    def __del__(self):
        del self.crs
        del self.sl
        del self.hf

    def join_centre(self):
        time.sleep(3)
        key_list = sorted(gl.KEYSDICT.iteritems(), key=lambda d:d[1]['priority'], reverse = False)

        data = {'ip':self.sysini['selfip'],'port':self.sysini['port'],'key':key_list[0][0],'priority':10,'threads':self.sysini['threads'],'mark':''}
        post_data={'serinfo':json.dumps(data)}
        try:
            response,content = self.hf.send_post(self.centreini['ip'],'join',self.sysini['port'],post_data)
            logger.info(content)
        except Exception as e:
            logger.error(e)

    def main(self):
        for i in self.sl.get_users():
            gl.KEYSDICT[i[1]] = {'priority':i[2],'multiple':i[3]}

        gl.THREADS = self.sysini.get('threads',4)
        gl.MAXSIZE = gl.THREADS*32  #�������������Ϊ�߳���32����
        gl.P_SIZE = {10:0,20:0,30:0} #Ȩ�޶�����
        #��������ʶ���߳�
        for c in range(gl.THREADS):
            RecgThread(c).start()

        t = threading.Thread(target=self.join_centre)
        t.start()      
        #web����
        server().start()

if __name__ == '__main__':  # pragma nocover
    initLogging(r'log\carrecgser.log')
    logger = logging.getLogger('root')
        
    rs = RecgServer()
    rs.main()

