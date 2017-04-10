import feedparser
import json
import functools
import queue
import threading
import time
import bs4
import pytz
import datetime
import urllib
import os
import pdb

import datafeed


class rfeed(object):


    def quit(self):
        if not self.feedcache:return
        historycache = self.getcachefile()
        if not os.path.exists(self.feedcache):
            os.mkdir(self.feedcache)
        with open(historycache,'w') as jh:
            for entry in self.history:
                time = entry.time
                del entry.__dict__['time']
                del entry.__dict__['times']
                del entry.__dict__['outtz']
                json.dump(entry.__dict__,jh)
                jh.write(os.linesep)


    def restore(self):
        if not self.feedcache:self.outq.put([])
        else:
            historycache = self.getcachefile()
            if os.path.exists(historycache):
                uids = []
                with open(historycache,'r') as jh:
                    cached = jh.readlines()
                    for line in cached:
                        edict = json.loads(line)
                        entry = datafeed.rfeedentry.from_dict(edict,self.outtz)
                        self.history.append(entry)
                        uids.append(entry.uid)
                self.entrycount = len(self.history)
                self.outq.put(uids)
            else:self.outq.put([])


    def getcachefile(self):
        cachetitle = self.title.replace(' ','_')
        historycache = os.path.join(self.feedcache,'%s.cache' % cachetitle)
        return historycache


    @staticmethod
    def tzshift(intime,outtz):
        outtime = datetime.datetime.strptime(intime,rfeed.indtformat)
        outtime = rfeed.utctz.localize(outtime).astimezone(outtz)
        return outtime


    indtformat = '%Y-%m-%dT%H:%M:%S+00:00'
    outdtformat = '%Y-%m-%d %H:%M:%S'
    utctz = pytz.timezone('UTC')
    

    def __init__(self,url,feedcache,tz = 'US/Eastern'):
        self.url = url
        self.feedcache = feedcache
        self.outtz = pytz.timezone(tz)
        self.entrycount = 0
        self.yieldcount = 0
        self.history = [] 
        self.inq = queue.Queue()
        self.outq = queue.Queue()
        self.feed = datafeed.feedthread(self.url,self.inq,self.outq)
        self.title,self.updated = self.inq.get(True)
        self.restore()
        self.getfeed()


    def getfeed(self):
        newentries = []
        while not self.inq.empty():
            entries,updated = self.inq.get(True)
            self.updated = updated
            newentries.extend(entries)
        if newentries:
            entries = [datafeed.rfeedentry(e,self.outtz) for e in newentries][::-1]
            entries = sorted(entries,key = lambda e : e.time)
            for j in range(len(entries)):
                titles = [e.title for e in self.history]
                if entries[j].title in titles:
                    which = titles.index(entries[j].title)
                    self.history[which].times.append(entries[j].time)
                    self.history[which].rawtimes.append(entries[j].rawtime)
                    self.history[which].users.extend(entries[j].users)
                    self.history[which].count += 1
                else:self.history.insert(0,entries[j])
            self.entrycount = len(self.history)


    def yieldfeed(self):
        piece = self.history[:self.entrycount-self.yieldcount]
        self.yieldcount = self.entrycount
        return piece


