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


class feedthread(threading.Thread):


    @staticmethod
    def validate(feed):
        return 'title' in feed['feed']


    @staticmethod
    def getfeed(url,delay):
        while True:
            feed = feedparser.parse(url)
            if feedthread.validate(feed):break
            else:
                print('... cannot yet reach url: %s ...' % self.url)
                time.sleep(delay)
        return feed


    def __init__(self,url,outq,inq,delay = 10):
        threading.Thread.__init__(self)
        self.stoprequest = threading.Event()
        self.url = url
        self.inq = inq
        self.outq = outq
        self.delay = delay
        self.start()


    def run(self):
        last = 0
        feed = feedthread.getfeed(self.url,self.delay)
        self.outq.put((feed['feed']['title'],feed['feed']['updated']))
        uids = self.inq.get(True)
        while not self.stoprequest.isSet():
            curr = time.time()
            wait = self.delay - (curr - last)
            if wait < 0:
                feed = feedthread.getfeed(self.url,self.delay)
                newes = []
                for e in feed['entries']:
                    if not e['id'] in uids:
                        newes.append(e)
                        uids.append(e['id'])
                self.outq.put((newes,feed['feed']['updated']))
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
        new = cls(None,outtz)
        keys = (
            'count','seen',
            'title','link','source','rawtime','rawtimes',
            'uid','users','userlinks',
                )
        for k in keys:new.__setattr__(k,d[k])
        new.time = rfeed.tzshift(new.rawtime,outtz)
        new.times = [new.time]
        return new


    @staticmethod
    def extractsource(link):
        source = link.replace('https','').replace('http','')
        source = source.replace('://','').replace('www.','')
        source = source[:source.find('.')]
        return source


    @staticmethod
    def extractarticle(link):
        req = urllib.request.Request(link,
            headers = {'User-Agent':'Magic Browser'}) 
        try:
            with urllib.request.urlopen(req) as wp:
                pagesoup = bs4.BeautifulSoup(wp.read(),'lxml')
        except urllib.error.HTTPError:
            print('httperror!',link)
            pdb.set_trace()
        ts = [t.string for t in pagesoup.find_all('title') if not t is None]
        ps = [p.string for p in pagesoup.find_all('p') if not p is None]
        '''#
        htmlpagefile = os.path.join(os.getcwd(),'.rsscache','pageexample.html.txt')
        textpagefile = os.path.join(os.getcwd(),'.rsscache','pageexample.text.txt')
        with open(htmlpagefile,'w') as f:
            f.write(link)
            f.write(os.linesep)
            f.write(pagesoup.prettify())
        with open(textpagefile,'w') as f:
            f.write(os.linesep.join(ps))
        '''#
        return ts,ps

    
    lineswhenselected = 3


    def __init__(self,raw,outtz):
        self.outtz = outtz
        self.count = 1
        self.seen = False
        if raw:
            self.title = raw['title']
            soup = bs4.BeautifulSoup(raw['summary'],'lxml')
            links = soup.find_all('a')
            self.link = links[-2].get('href')
            self.source = rfeedentry.extractsource(self.link)
            #self.article = rfeedentry.extractarticle(self.link)
            self.rawtime = raw['updated']
            self.rawtimes = [self.rawtime]
            self.time = rfeed.tzshift(self.rawtime,outtz)
            self.times = [self.time]
            self.uid = raw['id']
            self.users = [a['name'] for a in raw['authors']]
            self.userlinks = [a['href'] for a in raw['authors']]


    def getcolors(self,t):
        numcolor = t.bright_cyan
        tcolor = t.red if self.seen else t.green
        return numcolor,tcolor


    def titlelines(self,t,j,isselected,c,x):
        numcolor,tcolor = self.getcolors(t)
        timestamp = self.time.strftime(rfeed.outdtformat)
        if isselected:mods = (t.italic,t.bold,t.underline)
        else:mods = (t.italic,t.bold)
        mods = (t.italic,t.bold,t.underline) if isselected else (t.italic,t.bold)
        titleline = (
            ('{0:3d} | '.format(j+1),' | '.join([timestamp,self.title])),
            (numcolor,tcolor),(t.bold,mods))
        return [titleline]


    def linklines(self,t,j,isselected,c,x):
        numcolor,tcolor = self.getcolors(t)
        linkline = (
            ('    | ',' '*19+' | '+self.source+' | '+self.link),
            (numcolor,tcolor),(t.bold,(t.bold,t.italic)))
        return [linkline]


    def submissionlines(self,t,j,isselected,c,x):
        numcolor,tcolor = self.getcolors(t)
        subzip = zip(self.users,
            [i.strftime(rfeed.outdtformat) for i in self.times])
        info = ' | '.join(['{0} , {1}'.format(*i) for i in subzip])
        line = 'Submissions ({0:d}) | {1}'.format(self.count,info)
        subline = (
            ('    | ',' '*19+' | '+line),
            (numcolor,tcolor),(t.bold,(t.bold,t.italic)))
        return [subline]


    def output(self,t,p,j,isselected,c,x):
        lines = self.titlelines(t,j,isselected,c,x)
        if isselected:
            lines.extend(self.linklines(t,j,isselected,c,x))
            lines.extend(self.submissionlines(t,j,isselected,c,x))
        with t.location(0,p):
            for largs in lines:
                out(*largs+(c,x))
        return len(lines)


class rfeed(object):


    def scrollposition(self,v):
        head,tail = self.cache
        posmax = max(self.entrycount+len(head)+len(tail)-self.t.height,0)
        if v > 0:
            self.position = min(posmax,self.position+v)
            self.selected = max(self.selected,self.position)
        elif v < 0:
            self.position = max(0,self.position+v)
            spmax = self.position+self.t.height
            spmax -= len(head)+len(tail)+rfeedentry.lineswhenselected
            self.selected = min(self.selected,spmax)
        self.printfeed()


    def panposition(self,v):
        panxmax = 500
        if v > 0:self.panx = min(panxmax,self.panx+v)
        elif v < 0:self.panx = max(0,self.panx+v)
        self.printfeed()


    def scrollselected(self,v):
        head,tail = self.cache
        if v < 0:
            self.selected = max(self.position,self.selected+v)
        elif v > 0:
            spmax = self.position+self.t.height
            spmax -= len(head)+len(tail)+rfeedentry.lineswhenselected
            self.selected = min(self.entrycount-1,spmax,self.selected+v)
        self.printfeed()


    def scrollpage(self,v):
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
                        entry = rfeedentry.from_dict(edict,self.outtz)
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
    

    def __init__(self,t,url,feedcache,tz = 'US/Eastern'):
        self.t = t
        self.url = url
        self.feedcache = feedcache
        self.outtz = pytz.timezone(tz)
        self.entrycount = 0
        self.history = [] 
        self.position = 0
        self.panx = 0
        self.selected = 0
        self.page = (0,(0,1))

        self.inq = queue.Queue()
        self.outq = queue.Queue()
        self.feed = feedthread(self.url,self.inq,self.outq)
        self.title,self.updated = self.inq.get(True)
        self.restore()
        self.getfeed()


    def head(self):
        dtupdated = rfeed.tzshift(self.updated,self.outtz)
        dtupdated = dtupdated.strftime(self.outdtformat)
        headline = '||| Feed: %s | Updated: %s' % (self.title,dtupdated)
        head = ['-'*500,headline,'-'*500]
        return head


    def tail(self):
        c,r = self.t.width,self.t.height
        keystring = '||| q : quit | j : move down | k : move up'
        keystring += ' | l : scroll down | h : scroll up | c : mark selected'
        keystring += ' | , : page down | . : page up'
        windowstring = ('||| position : %d' % (self.position+1))
        windowstring += (' | selected : %d' % (self.selected+1))
        windowstring += (' | page : %d/%d' % (self.page[0]+1,self.page[1][-1]+1))
        windowstring += (' | entrycount : %d' % self.entrycount)
        windowstring += (' | windowsize  : %s' % str((c,r)))
        tail = ['-'*500,keystring,windowstring,'-'*500]
        return tail


    def getfeedstats(self):
        '''
        want to track number of posts per unit time (hr?) for
            any users, any sources, any article links, 
            or combinations thereof?

        each unique user, source, or article link becomes a key in a dict
        this includes an ALLUSERS, ALLSOURCES, or ALLLINKS entry
        scanning over all entries, bin onto a time axis

        produce matplotlib plots of the data?
        '''
        pdb.set_trace()


    def getfeed(self):
        newentries = []
        while not self.inq.empty():
            entries,updated = self.inq.get(True)
            self.updated = updated
            newentries.extend(entries)
        if newentries:
            entries = [rfeedentry(e,self.outtz) for e in newentries][::-1]
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
        #self.getfeedstats()
        head = self.head()
        tail = self.tail()
        self.cache = (head,tail)
        return self.cache


    def printfeed(self):
        c,r = self.t.width,self.t.height
        head,tail = self.getfeed()
        with self.t.location(0,0):
            for line in head:
                out([line],[self.t.bright_cyan],[self.t.bold],c)
        j,k = self.position,self.position-len(head)-len(tail)+r
        while j < k:
            p = len(head)+j-self.position
            if j < self.entrycount:
                if self.page[0] == 0:
                    j += self.history[j].output(self.t,
                        p,j,j == self.selected,c,self.panx)
                elif self.page[0] == 1:
                    with self.t.location(0,p):
                        out(['XXX | '],[self.t.bright_cyan],[self.t.bold],c)
                        j += 1
            else:
                with self.t.location(0,p):
                    out(['    | '],[self.t.bright_cyan],[self.t.bold],c)
                    j += 1
        with self.t.location(0,r-len(tail)):
            for line in tail:
                out([line],[self.t.bright_cyan],[self.t.bold],c)


fseq = lambda i,s : functools.reduce(lambda x,f : f(x),[i]+list(s))
def out(strings,colors,mods,c,panx = 0):
    '''Print a single line to stdout with specified colors and modifiers.
    colors  : list of colors 1 - 1 with strings
    mods    : list of lists of mods 1 - 1 with strings
    strings : list of strings composing a single line of output
    '''
    fill = c
    keepers = []
    for s in strings:
        slen = len(s)
        if panx >= slen:
            panx -= slen
            colors = colors[1:]
            mods = mods[1:]
        elif panx:keepers.append(s[panx:])
        else:keepers.append(s)
    for c,m,s in zip(colors,mods,keepers):
        if m is None:mod = lambda x : x
        elif type(m) in (type([]),type(())):mod = lambda x : fseq(x,m)
        else:mod = m
        print(mod(c(s[:min(len(s),fill)])),end = '')
        fill -= len(s)
    if fill:print(' '*fill,end = '')


