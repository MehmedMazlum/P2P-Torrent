import threading
from multiprocessing import Queue
import socket
import time
import sqlite3
from sqlite3 import Error
from uuid import getnode as get_mac
import glob, os

import sys

from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QListWidget

import mainwindow

logQueue = Queue()
interfaceQueue = Queue()
writers = {}
quitflag = 0
peers = {}
files = {}
downloadings = {}

def create_db(db_file):
    """ create a database connection to a SQLite database """
    try:
        conn = sqlite3.connect(db_file)
        print(sqlite3.version)
    except Error as e:
        print(e)
    finally:
        conn.close()
def create_table(db_file):
    """ create a database connection to a SQLite database """
    try:
        conn = sqlite3.connect(db_file)
        #print(sqlite3.version)
        with conn:
            cur = conn.cursor()
            print("calıstım")
            cur.execute("CREATE TABLE [peers] ([peer_id] INTEGER  PRIMARY KEY NULL,[uuid] INTEGER NULL,[ip] TEXT  NULL,[port] INTEGER  NULL")
            control=False
    except Error as e:
        print(e)
    finally:
        conn.close()

###veri tabanına peer eklemek için
def insert_peers(self,uuid,ip,port):
    conn = sqlite3.connect(db_file)
    #print(sqlite3.version)
    cur = conn.cursor()
    with conn:

        self.cur.execute("""INSERT INTO peers VALUES(NULL,?,?,?)""", (uuid,ip,port))
        self.conn.commit()
        return "Succ"


#########veri tabını boş mu dolu mu???
def control(db_file):
    try:
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()
        #print(sqlite3.version)
        cur.execute("SELECT  *from peers ")

        data = cur.fetchall()
        #return len(data)
        if len(data) >= 1:
            return False
        else:
            return True

    except Error as e:
        print(e)



#########veri tabında daha önce eklenme varsa bunları peers dict yazacak server açılıp kapanınca peer listesi unutulmaın diye
def egaliser_db(db_file):
    conn = sqlite3.connect(db_file)
    cur = con.cursor()

    cur.execute("SELECT  *from peers  ")
    data = cur.fetchall()
    # print("len data", len(data))
    size = len(data)
    for i in range(size):
        peers.setdefault(data[i][1], []).append(data[i][2])
        peers.setdefault(data[i][1], []).append(data[i][3])

class loggerThread (threading.Thread):

    def __init__(self, name, logQueue):
        threading.Thread.__init__(self)
        self.name = name
        self.lQueue = logQueue

    def run(self):
        print("Starting " + self.name)
        with open('logs.txt', 'a') as f:
            while True:
               msg = self.lQueue.get()
               if msg != "":
                    t = time.ctime()
                    msg = msg.strip()
                    log = str(t) + " : " + str(msg) + "\n"
                    f.write(log)
                    print(log)
                    if msg == "QUIT":
                        f.close()
                        break

class writeThread(threading.Thread):
    def __init__(self, sc, writerQueue, addr):
        threading.Thread.__init__(self)
        self.s = sc
        self.wQueue = writerQueue

    def run(self):
        global quitflag
        while True:
            unparsedmsg = self.wQueue.get()
            #print(unparsedmsg)
            if(unparsedmsg == "QUIT"):
                logQueue.put("Exiting WriterThread - ")
                self.s.close()
                return True
            else:
                self.s.send(unparsedmsg.encode())

class connectionThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        global quitflag
        while True:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            host = "0.0.0.0"
            port = 11121
            s.bind((host, port))
            s.listen(5)

            counter = 1
            db_file = "./users1.db"
            print("control", control(db_file))
            if control(db_file) == None:
                #print("çalıştım")
                create_table(db_file)
            #create_db("./users1.db")

            while True:
                try:
                    threadQueue = Queue()
                    logQueue.put("Waiting for connections.")
                    c, addr = s.accept()
                    logQueue.put("Got connection from" + str(addr))
                    # writers[addr] = threadQueue
                    time=TimeThread("Time thread-"+ str(counter),host,port)
                    time.start()
                    logQueue.put("Starting ReaderThread - " + str(counter))
                    rThread = readerThread(c, threadQueue, addr)
                    rThread.start()
                    logQueue.put("Starting WriterThread - " + str(counter))
                    wThread = writeThread(c, threadQueue, addr)
                    wThread.start()
                    counter += 1
                except KeyboardInterrupt:
                    s.close()
                    logQueue.put('QUIT')
                    break
####zamanı geçmiş olanları siliyoruz
class TimeThread(threading.Thread):
    def __init__(self, name, cplLock, ip, port):
        threading.Thread.__init__(self)
        self.name = name
        #self.cplLock = cplLock
        self.ip = ip
        self.port = port

    def run(self):
        print("Starting " + self.name)
        while True:
            time.sleep(20)  # 20s just to test
            delQueue = queue.Queue()


            for key, value in list(peers.items()):
                if (str(value[0]) != self.ip or int(value[1])!= self.port):
                    try:
                        testSocket = socket.socket()
                        testSocket.settimeout(5)
                        testSocket.connect((str(value[0]),int(value[1])))
                        testSocket.send("TIC".encode())
                        data = testSocket.recv(1024).decode()
                        if data[0:5] == "TOC":
                            pass
                        else:
                            delQueue.put((value[0], value[1]))
                        testSocket.send("BYBY".encode())

                    except:
                        delQueue.put(value[0], value[1])
            while not delQueue.empty():
                delIndex = delQueue.get()
                for key, value in list(peers.items()):
                    if (delIndex[0] == value[0] and int(delIndex[1]) == value[1]):
                        print("siliyorum ",peers[key])
                        del peers[key]
                        break
class readerThread(threading.Thread):
    def __init__(self, sc, threadQueue, addr):
        threading.Thread.__init__(self)
        self.s = sc
        self.uuid = ""
        self.tQueue = threadQueue
        self.ip = addr[0]
        self.port = addr[1]

    def run(self):
        while True:
            unparsedmsg = self.s.recv(1024).decode()
            #print(unparsedmsg)
            parsedmsg = self.outgoingParser(unparsedmsg)
            if(parsedmsg == "QUI"):
                logQueue.put("Exiting ReaderThread - " + str(self.number))
                return True


    def outgoingParser(self, msg):
        global quitflag
        msgList = msg.split(" ")
        #print(msgList[0].strip())
        #print(len(msgList))
        cmd = msgList[0].strip()
        #print(cmd)
        msgList.pop(0)
        if cmd == "USR":
            uuid = msgList[0]
            self.uuid = uuid
            self.tQueue.put("TIC")
        if cmd == "TOC":
            #timer eklenecek
            peers.setdefault(self.uuid, []).append(self.ip)
            peers.setdefault(self.uuid, []).append(self.port)
            #########veri tabanı ve peers listesi eşitlemeye çalışıyoruz
            insert_peers(self.uuid, self.ip, self.port)
            #db'ye yaz
            #db'ye yaz
        if cmd == "TIC":
            self.tQueue.put("TOC " + str(get_mac()))
        if cmd == "SUCC":
            self.tQueue.put("LSQ")
        if cmd == "LSA":
            pList = msgList[0].split(":")
            for x in pList:
                pString = x.split(",")
                uuid = pString[0]
                if uuid:
                    ip = pString[1]
                    port = pString[2]
                    peers.setdefault(uuid, []).append(ip)
                    peers.setdefault(uuid, []).append(port)
                    #print(peers)
        if cmd == "SEA":
            fname = msgList[0]
            ret = search_file(fname)
            #TODO: 0 olma durumunu yap
            if ret:
                self.tQueue.put("ASE " + ret)
        if cmd == "ASE":
            fString = msgList[0]
            print("Fstring = " + fString)
            fList = fString.split(":")
            for x in fList[:-1]:
                print(x.split(","))
                fname = x.split(",")[0]
                fmd5 = x.split(",")[1]
                fsize = x.split(",")[2].strip()
                files.setdefault(fname, []).append(fmd5)
                files.setdefault(fname, []).append(fsize)
            #print(files)
            interfaceQueue.put(fString)
        if cmd == "SMD":
            md5 = msgList[0]
            ret = search_file_md5(md5)
            if ret:
                self.tQueue.put("VAR " + str(md5))
            else:
                self.tQueue.put("YOH")
        if cmd == "VAR":
            downloadings[md5].append(self.ip)

def get_cList (ip, port):
    threadQueue = Queue()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host = ip
    s.connect_ex((host, port))
    print("Socket established with" + ip)
    rThread = readerThread(s, threadQueue, (ip, port))
    rThread.start()
    wThread = writeThread(s, threadQueue, (ip, port))
    wThread.start()
    threadQueue.put("USR " + str(get_mac()))
    #TODO : Socket kapatilacak
    #threadQueue.put("QUIT")

def findFile(fname):
    for key, value in peers.items():
        print(key)
        print(get_mac())
        mac = get_mac()
        print(key!=mac) #bunu arastir
        if key != mac:
            threadQueue = Queue()
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            ip = value[0]
            host = ip
            port = 11121
            s.connect_ex((host, port))
            print("Socket established with" + ip)
            rThread = readerThread(s, threadQueue, (ip, port))
            rThread.start()
            wThread = writeThread(s, threadQueue, (ip, port))
            wThread.start()
            threadQueue.put("SEA " + fname)

def search_file(sname):
    # s = ""`
    # for file in glob.glob("*.txt"):
    #     print(file)
    #     s = s + file + ","
    # if s:
    #     return s
    # else:
    #     return 0
    s = ""
    os.chdir(sys.path[0] + "/shared")
    with open('files.txt', 'r') as f:
        for line in f:
            fcredentials = line.split(":")
            fnameex = fcredentials[0]
            fname = fcredentials[0].split(".")[0]
            fmd5 = fcredentials[1]
            fsize = fcredentials[2]
            if sname == fname:
                s = s + fnameex + "," + fmd5 + "," + fsize + ":"
        f.close()
    if s:
        return s
    else:
        return 0

def search_file_md5(md5):
    # s = ""
    # for file in glob.glob("*.txt"):
    #     print(file)
    #     s = s + file + ","
    # if s:
    #     return s
    # else:
    #     return 0
    s = ""
    os.chdir(sys.path[0] + "/shared")
    with open('files.txt', 'r') as f:
        for line in f:
            fcredentials = line.split(":")
            fnameex = fcredentials[0]
            fname = fcredentials[0].split(".")[0]
            fmd5 = fcredentials[1]
            if fmd5 == md5:
                f.close()
                return 1
        f.close()
    return 0

def findFilemd5(md5):
    for key, value in peers.items():
         # TODO: bunu arastir
        if key != get_mac():
            threadQueue = Queue()
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            ip = value[0]
            host = ip
            port = 11121
            #s.connect_ex((host, port))
            print("Socket established with" + ip)
            rThread = readerThread(s, threadQueue, (ip, port))
            rThread.start()
            wThread = writeThread(s, threadQueue, (ip, port))
            wThread.start()
            threadQueue.put("SMD " + files[md5.text()][0])


def start_download(md5):
    print(md5.text())
    print(11111)



lThread = loggerThread("Logger", logQueue)
lThread.start()


counter = 1

#create_db("./users.db")