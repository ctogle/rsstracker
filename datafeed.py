import feedparser
import json
import functools
import blessed
import queue
import threading
import time
import bs4
import pytz
import datetime
import shutil
import os
import pdb


class feedthread(threading.Thread):


    @staticmethod
    def validate(feed):
        return 'title' in feed['feed']


    def __init__(self,url,q,delay = 5):
        threading.Thread.__init__(self)
        self.stoprequest = threading.Event()
        self.url = url
        self.q = q
        self.delay = delay
        self.start()


    def join(self,timeout = None):
        self.stoprequest.set()
        threading.Thread.join(self,timeout)


    def run(self):
        last = 0
        while not self.stoprequest.isSet():
            curr = time.time()
            wait = self.delay - (curr - last)
            if wait < 0:
                feed = feedparser.parse(self.url)
                if feedthread.validate(feed):
                    self.q.put((self.name,feed))
                    last = curr
            else:time.sleep(0.1)


class rfeedentry(object):


    def __eq__(self,other):
        if isinstance(other,self.__class__):
            return self.uid == other.uid
        return NotImplemented


    def __ne__(self,other):
        if isinstance(other,self.__class__):
            return not self.__eq__(other)
        return NotImplemented


    def __hash__(self):
        return hash(self.uid)


    @classmethod
    def from_dict(cls,d,outtz):
        new = cls(d['raw'],outtz)
        for k in ('count','seen'):
            new.__setattr__(k,d[k])
        return new

    
    def __init__(self,raw,outtz):
        self.raw = raw

        soup = bs4.BeautifulSoup(raw['summary'],'lxml')
        links = soup.find_all('a')
        self.source = links[-2].get('href')

        self.time = rfeed.tzshift(raw['updated'],outtz)
        self.uid = raw['title']
        self.count = 1
        self.seen = False


    def output(self,t,j,isselected,c):
        timestamp = self.time.strftime(rfeed.outdtformat)
        numcolor = t.bright_cyan
        tcolor = t.bright_red if self.seen else t.bright_green

        titleline = (
            ('{0:3d} | '.format(j+1),' | '.join([timestamp,self.raw['title']])),
            (numcolor,tcolor),(t.bold,(t.italic,t.bold)))
        lines = [titleline]

        if isselected:
            linkline = (
                ('    | ',' '*19+' | '+self.source),
                (numcolor,tcolor),(t.bold,t.italic))
            lines.append(linkline)

        for largs in lines:out(*largs+(c,))
        return -(len(lines)-1)


class rfeed(object):


    def scrollposition(self,v):
        c,r = shutil.get_terminal_size()
        head,tail = self.cache
        posmax = max(self.entrycount+len(head)+len(tail)-r,0)
        if v > 0:
            self.position = min(posmax,self.position+v)
            self.selected = max(self.selected,self.position)
        elif v < 0:
            self.position = max(0,self.position+v)
            spmax = self.position+r-len(head)-len(tail)-2
            self.selected = min(self.selected,spmax)
        self.printfeed()


    def scrollselected(self,v):
        c,r = shutil.get_terminal_size()
        head,tail = self.cache
        if v < 0:
            self.selected = max(self.position,self.selected+v)
        elif v > 0:
            spmax = self.position+r-len(head)-len(tail)-2
            self.selected = min(self.entrycount-1,spmax,self.selected+v)
        self.printfeed()


    def scrollpage(self,v):
        c,r = shutil.get_terminal_size()
        newpage = self.page[0]+v
        if newpage < self.page[1][0]:newpage = self.page[1][-1]
        elif newpage > self.page[1][-1]:newpage = self.page[1][0]
        self.page = (newpage,self.page[1])
        self.printfeed()


    def togglemarkselected(self):
        entry = self.history[self.selected]
        entry.seen = not entry.seen
        self.printfeed()


    def quit(self):
        self.feed.join()
        if not self.feedcache:return
        historycache = self.getcachefile()
        if not os.path.exists(self.feedcache):
            os.mkdir(self.feedcache)
        with open(historycache,'w') as jh:
            for entry in self.history:
                time = entry.time
                del entry.__dict__['time']
                json.dump(entry.__dict__,jh)
                jh.write(os.linesep)


    def restore(self):
        historycache = self.getcachefile()
        if not os.path.exists(historycache):return
        with open(historycache,'r') as jh:
            cached = jh.readlines()
            for line in cached:
                entry = rfeedentry.from_dict(json.loads(line),self.outtz)
                self.history.append(entry)
        self.entrycount = len(self.history)


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
    

    def __init__(self,t,url,feedcache,tz = 'US/Eastern'):
        self.t = t
        self.url = url
        self.feedcache = feedcache
        self.outtz = pytz.timezone(tz)
        self.entrycount = 0
        self.history = [] 
        self.queue = queue.Queue()
        self.feed = feedthread(self.url,self.queue)
        self.position = 0
        self.selected = 0
        self.page = (0,(0,1))
        while self.queue.empty():
            time.sleep(0.1)
        self.getfeed(*shutil.get_terminal_size())
        if feedcache:self.restore()


    def head(self,c,r):
        dtupdated = rfeed.tzshift(self.updated,self.outtz)
        dtupdated = dtupdated.strftime(self.outdtformat)
        headline = '||| Feed: %s | Updated: %s' % (self.title,dtupdated)
        head = ['-'*c,headline,'-'*c]
        return head


    def tail(self,c,r):
        keystring = '||| q : quit | j : move down | k : move up'
        keystring += ' | l : scroll down | h : scroll up | c : mark selected'
        keystring += ' | , : page down | . : page up'
        windowstring = ('||| position : %d' % (self.position+1))
        windowstring += (' | selected : %d' % (self.selected+1))
        windowstring += (' | page : %d/%d' % (self.page[0]+1,self.page[1][-1]+1))
        windowstring += (' | entrycount : %d' % self.entrycount)
        windowstring += (' | windowsize  : %s' % str((c,r)))
        tail = ['-'*c,keystring,windowstring,'-'*c]
        return tail


    def getfeed(self,c,r):
        newentries = []
        while not self.queue.empty():
            threadname,feed = self.queue.get(True)
            self.title = feed['feed']['title']
            self.updated = feed['feed']['updated']
            newentries.extend(feed['entries'])
        if newentries:
            entries = [rfeedentry(e,self.outtz) for e in newentries][::-1]
            entries = sorted(entries,key = lambda e : e.time)
            for j in range(len(entries)):
                if entries[j] in self.history:
                    which = self.history.index(entries[j])
                    self.history[which].count += 1
                else:
                    self.history.insert(0,entries[j])
            self.entrycount = len(self.history)
        head = self.head(c,r)
        tail = self.tail(c,r)
        self.cache = (head,tail)
        return self.cache


    def printfeed(self):
        c,r = shutil.get_terminal_size()
        head,tail = self.getfeed(c,r)
        with self.t.location(0,0):
            for line in head:
                out([line],[self.t.bright_cyan],[self.t.bold],c)
        with self.t.location(0,len(head)):
            j,k = self.position,self.position-len(head)-len(tail)+r
            while j < k:
                if j < self.entrycount:
                    if self.page[0] == 0:
                        entry = self.history[j]
                        k += entry.output(self.t,j,j == self.selected,c)
                    elif self.page[0] == 1:
                        out(['XXX | '],[self.t.bright_cyan],[self.t.bold],c)
                else:out(['    | '],[self.t.bright_cyan],[self.t.bold],c)
                j += 1
        with self.t.location(0,r-len(tail)):
            for line in tail:
                out([line],[self.t.bright_cyan],[self.t.bold],c)


fseq = lambda i,s : functools.reduce(lambda x,f : f(x),[i]+list(s))
def out(strings,colors,mods,c):
    '''Print a single line to stdout with specified colors and modifiers.
    colors  : list of colors 1 - 1 with strings
    mods    : list of lists of mods 1 - 1 with strings
    strings : list of strings composing a single line of output
    '''
    fill = c
    for c,m,s in zip(colors,mods,strings):
        if m is None:mod = lambda x : x
        elif type(m) in (type([]),type(())):mod = lambda x : fseq(x,m)
        else:mod = m
        print(mod(c(s[:min(len(s),fill)])),end = '')
        fill -= len(s)
    if fill:print(' '*fill,end = '')


