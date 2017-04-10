#!/usr/bin/env python3
import os,argparse,blessed,pdb
import datafeed2 as datafeed
import interface
from interface import text


def scrollfeed(v):
    newlive = args.current+v
    if newlive < 0:newlive = len(rfeeds)-1
    elif newlive >= len(rfeeds):newlive = 0
    return newlive


def geturls(urlspath):
    urls = []
    if not os.path.exists(urlspath):
        raise IOError('... URLs file \'%s\' is missing ...' % urlspath)
    with open(urlspath,'r') as h:
        for line in h.readlines():
            l = line.strip()
            if not l or l.startswith('#'):continue
            else:urls.append(l)
    assert len(urls) > 0
    return tuple(urls)


def quitfeeds(a):
    for rf in rfeeds:rf.quit()
    for rf in rfeeds:rf.feed.stoprequest.set()
    for rf in rfeeds:rf.feed.join()


def headcontent(b):
    for rf in rfeeds:rf.getfeed()
    rfeed = rfeeds[args.current]
    dtupdated = rfeed.tzshift(rfeed.updated,rfeed.outtz)
    dtupdated = dtupdated.strftime(rfeed.outdtformat)
    headline = '  Feed Title: "%s"  |  Updated: %s' % (rfeed.title,dtupdated)
    b.content = [text(headline,t.bold,t.cyan)]
    b.needdraw = True


def leftinkey(b,key):
    if   key == '.':args.current = scrollfeed( 1)
    elif key == ',':args.current = scrollfeed(-1)
    return key


def leftcontent(b):
    rfeed = rfeeds[args.current]
    newentries = rfeed.yieldfeed()
    for e in newentries[::-1]:
        etime = e.time.strftime(rfeed.outdtformat)
        etitle = e.title
        titleline = text(etime+' | '+etitle,t.bold,t.green)
        front = numbase(len(leftcontents[args.current]),b)
        entrycontent = front+titleline
        leftcontents[args.current].append(entrycontent)
    if newentries:
        b.content = leftcontents[args.current][::-1]
        b.needdraw = True


def rightinkey(b,key):
    if   key == '.':args.current = scrollfeed( 1)
    elif key == ',':args.current = scrollfeed(-1)
    return key


def rightcontent(b):
    rfeed = rfeeds[args.current]

    newentries = rfeed.yieldfeed()
    for e in newentries[::-1]:
        etime = e.time.strftime(rfeed.outdtformat)
        etitle = e.title
        titleline = text(etime+' | '+etitle,t.bold,t.green)
        front = numbase(len(rightcontents[args.current]),b)
        entrycontent = front+titleline
        rightcontents[args.current].append(entrycontent)
    b.content = rightcontents[args.current][::-1]
    b.needdraw = True


def tailcontent(b):
    rfeed = rfeeds[args.current]
    tail = '  Entry Count: %d  |  Window Size: %s'
    tail = tail % (rfeed.entrycount,str((t.width,t.height)))
    b.content = [text(tail,t.bold,t.cyan)]
    b.needdraw = True


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-u','--urlspath',
        default = os.path.join(os.getcwd(),'urls'),
        help = 'path to file enumerating rss feed urls')
    parser.add_argument('-d','--feedcache',
        default = os.path.join(os.getcwd(),'.rsscache'),
        help = 'directory in which to store rss feed histories')
    parser.add_argument('-c','--current',
        default = 0,type = int,
        help = 'which feed is current at startup')
    args = parser.parse_args()

    urls = geturls(args.urlspath)
    rfeeds = tuple((datafeed.rfeed(u,args.feedcache) for u in urls))
    leftcontents = [[] for rf in rfeeds]
    rightcontents = [[] for rf in rfeeds]
    numbase = lambda j,b : text('{0:3d}|| '.format(j+1),t.bold,t.cyan)

    t = blessed.Terminal()
    a = interface.app(t,selected = 2,quitcb = quitfeeds)


    head = a.abox(h = 3,anchor = (-1,-1),selectable = False,cb = headcontent)

    left = a.abox(y = 0,anchor = (-1, 0),maxw = -50,maxh = -6,
        cb = leftcontent,inkey = leftinkey)

    right = a.abox(y = 0,anchor = (1, 0),maxw = 50,maxh = -6,
        cb = rightcontent,inkey = rightinkey)

    tail = a.abox(h = 3,anchor = (-1, 1),selectable = False,cb = tailcontent)


    a.run()
