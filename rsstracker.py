#!/usr/bin/env python3
import os,argparse,blessed,pdb
import datafeed


def scrollfeed(v):
    newlive = live+v
    if newlive < 0:newlive = len(rfeeds)-1
    elif newlive >= len(rfeeds):newlive = 0
    return newlive


def geturls(urlspath):
    urls = []
    with open(urlspath,'r') as h:
        for line in h.readlines():
            l = line.strip()
            if not l or l.startswith('#'):continue
            else:urls.append(l)
    assert len(urls) > 0
    return tuple(urls)


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

    t = blessed.Terminal()
    live = args.current
    urls = geturls(args.urlspath)
    rfeeds = tuple((datafeed.rfeed(t,u,args.feedcache) for u in urls))
    with t.fullscreen():
        with t.hidden_cursor():
            while True:
                rfeed = rfeeds[live]
                rfeed.printfeed()
                with t.cbreak():
                    key = t.inkey(timeout = 0.5)
                    if   key == 'h':rfeed.scrollselected(-1)
                    elif key == 'l':rfeed.scrollselected(1)
                    elif key == 'j':rfeed.scrollposition(1)
                    elif key == 'k':rfeed.scrollposition(-1)
                    elif key == ',':rfeed.scrollpage(-1)
                    elif key == '.':rfeed.scrollpage(1)
                    elif key == 'c':rfeed.togglemarkselected()
                    elif key == '[':live = scrollfeed(-1)
                    elif key == ']':live = scrollfeed(1)
                    elif key == 'q':
                        for rf in rfeeds:rf.quit()
                        break


