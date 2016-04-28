#!/usr/bin/env python

#  A Utility script with functions to create locks in a safe way for running processes. 
#  Will ensure only the process that has
#  obtained the lock with registerPid() is the only one that runs. 
#  registerPid(),unregisterPid() will be called from the parent process

import os, os.path
from fcntl import LOCK_UN, LOCK_EX,LOCK_NB, flock 

#import struct
#MAXPIDBYTE=struct.calcsize("P")
MAXPIDBYTE=8
MAXPID=65536


def __lockFile(fd,nonBlock=True):
	try:
		if nonBlock:
			flock(fd,LOCK_EX|LOCK_NB)
		else:
			flock(fd,LOCK_EX)
	except Exception,e:
		return False
	return True

def __unLockFile(fd):
	flock(fd, LOCK_UN)

def registerPid(pidFile, forceRun=False):
	pid = os.getpid()
	try:
		fd=os.open(pidFile, os.O_CREAT|os.O_WRONLY|os.O_EXCL)
		if __lockFile(fd):
			os.write(fd, str(pid))
			__unLockFile(fd)
			os.close(fd)
			return True
	except OSError, e:
		if e.errno == os.errno.EEXIST:
			#read pid from existing file
			try:
				fd=os.open(pidFile, os.O_RDWR|os.O_EXCL|os.O_NONBLOCK)
				if __lockFile(fd):
					os.lseek(fd,0,0)
					opid=os.read(fd,MAXPIDBYTE)
					
					#Check if opid is currently running process
					#otherwise no other instance is running, write current pid
					#to the file and return True
					try:
						if opid.strip() == "":
							opid = MAXPID + 1
						else:	
							opid = int(opid)
								
						os.kill( opid,0)
					except OSError, e:
						if e.errno == os.errno.ESRCH:
							os.ftruncate(fd,0)
							os.lseek(fd,0,0)
							spid=str(pid)
							os.write(fd, spid)
							__unLockFile(fd)
							os.close(fd)
							return True
						else:
							raise OSError(e)

					
				
				#Else another process is running or has locked pidFile
			except OSError,e:
				#file has been opened by another process
				if e.errno == os.errno.EBUSY:
					return forceRun
				else:
					raise OSError(e)

			finally:
				try: 
					os.close(fd)
				except:
					pass

	return forceRun

def unregisterPid(pidFile):
		pid=os.getpid()
		try:
			#Open file, obtain lock and remove if this test process owns it
			#This will block. Not sure O_EXCL is not ignored
			fd= os.open(pidFile, os.O_RDONLY|os.O_EXCL) 
			if __lockFile(fd, False):
				apid = os.read(fd,MAXPIDBYTE)
				if str(pid) == apid.strip():
					__unLockFile(fd)
					os.close(fd)
					os.remove(pidFile)
				else:
					__unLockFile(fd)
					os.close(fd)
		except Exception, e:
				pass
						
