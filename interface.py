import blessed,signal,functools,pdb


def clip(t,x,y,content,xfill = None,yfill = None):
    if yfill is None:yfill = t.height
    if xfill is None:xfill = t.width
    for j,line in enumerate(content):
        if y+j < 0:continue
        with t.location(max(0,x),y+j):
            if not (-x >= len(line) or x > t.width):
                if x < 0:line = line[-x:]
                l = line[:min(len(line),xfill)]
                print(l,end = '')


def border(t,border):
    hb,vb,cb = border
    with t.location(0,0):
        print(cb+(t.width-2)*hb+cb,end = '')
    for j in range(1,t.height-1):
        with t.location(0,j):
            print(vb,end = '')
        with t.location(t.width,j):
            print(vb,end = '')
    with t.location(0,t.height-1):
        print(cb+(t.width-2)*hb+cb,end = '')


class text(object):

    
    def __repr__(self):
        fseq = lambda i,s : functools.reduce(lambda x,f : f(x),[i]+list(s))
        out = ''
        for j,piece in enumerate(zip(self.s,self.m,self.c)):
            s,m,c = piece
            if m is None:mod = lambda x : x
            elif type(m) in (type(()),type(())):
                mod = lambda x : fseq(x,[f for f in m if not f is None])
            else:mod = m
            if c is None:col = lambda x : x
            else:col = c
            out += mod(col(s))
        return out


    def __len__(self):
        return sum([len(s) for s in self.s])


    def __getitem__(self,x):
        if isinstance(x,slice):
            if len(self.s) == 1:return text(self.s[0][x],self.m,self.c)
            slens = [len(s) for s in self.s]
            st,ed = x.start,x.stop
            #splens = list(map(lambda j : sum(slens[:j+1]),range(len(slens))))
            if (st == 0 or st is None) and (ed == sum(slens) or ed is None):
                return text(self.s[:],self.m[:],self.c[:])
            news,newm,newc = [],[],[]
            for j in range(len(self.s)):
                slen = slens[j]
                if st is None or st < slen:
                    if st is None or st < 0:tst = None
                    else:tst = st
                    if ed is None or ed > slen:ted = None
                    else:ted = ed
                    tslice = slice(tst,ted,None)
                    news.append(self.s[j][tslice])
                    newm.append(self.m[j])
                    newc.append(self.c[j])
                    if not st is None:st -= slen-len(news[-1])
                    if not ed is None:ed -= slen-len(news[-1])
                else:
                    if not st is None:st -= slen
                    if not ed is None:ed -= slen
            return text(tuple(news),tuple(newm),tuple(newc))
        else:
            print('issue',type(x))
            pdb.set_trace()
            raise NotImplementedError


    def __new__(cls,s,m = None,c = None):
        t = object.__new__(cls)
        t.s = s if type(s) == type(()) else (s,)
        t.m = m if type(m) == type(()) else ((m,),)
        t.c = c if type(c) == type(()) else (c,)
        return t


    def __radd__(self,o):
        if type(o) == type(''):
            return text(o+self.s[0],self.m[:],self.c[:])
        else:
            if type(o) == type(()):s,m,c = o
            elif isinstance(o,text):s,m,c = o.s,o.m,o.c
        return text(s+self.s,m+self.m,c+self.c)


    def __add__(self,o):
        if type(o) == type(''):
            return text(self.s[0]+o,self.m[:],self.c[:])
        else:
            if type(o) == type(()):s,m,c = o
            elif isinstance(o,text):s,m,c = o.s,o.m,o.c
        return text(self.s+s,self.m+m,self.c+c)


class box(object):


    def overlap(self,o):
        if   self.x+self.w < o.x or self.x > o.x+o.w:return False
        elif self.y+self.h < o.y or self.y > o.h+o.h:return False
        else:return True


    def __setattr__(self,k,v):
        object.__setattr__(self,k,v)
        if k == 'needdraw' and not self.selected:
            self.app.needdraw = True
            if self.needdraw and not self.index == len(self.app.boxes):
                for o in self.app.boxes[self.index+1:]:
                    if self.overlap(o):
                        o.needdraw = True


    def __getattribute__(self,k):
        v = object.__getattribute__(self,k)
        if k == 'w' and v is None:
            return min(self.app.t.width,self.maxw)
        if k == 'h' and v is None:
            return min(self.app.t.height,self.maxh)
        if k == 'maxw' and v < 0:
            return self.app.t.width+v
        if k == 'maxh' and v < 0:
            return self.app.t.height+v
        anchor = object.__getattribute__(self,'anchor')
        if anchor and (k == 'x' or k == 'y'):
            xa,ya = anchor
            if   k == 'x':
                if   xa == -1:return 0
                elif xa ==  0:return (self.app.t.width-self.w)//2
                elif xa ==  1:return (self.app.t.width-self.w)
            elif k == 'y':
                if   ya == -1:return 0
                elif ya ==  0:return (self.app.t.height-self.h)//2
                elif ya ==  1:return (self.app.t.height-self.h)
        else:return v


    def __init__(self,a,c,x,y,w,h,maxw = 1000,maxh = 1000,b = ('=','|','#'),
            cb = None,inkey = None,f = ' ',fixed = False,anchor = None):
        self.app = a
        self.index = len(a.boxes)
        self.content = c
        self.fixed = fixed
        self.anchor = anchor
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.maxw = maxw
        self.maxh = maxh
        self.b = b
        self.f = f
        self.selected = False
        self.needdraw = True
        self.callback = cb
        self.inkey = inkey

    
    def print(self,t,x,y):
        if self.fixed or self.anchor:x,y = 0,0
        if self.selected:bc = t.cyan
        else:bc = t.red
        hb,vb,cb = self.b
        lines = []
        lines += [text(cb+hb*(self.w-2)+cb,t.bold,bc)]
        r = self.h-2
        for j,c in enumerate(self.content):
            if r == 0:break
            l = c[:min(len(c),self.w-2)]+max(0,self.w-2-len(c))*self.f
            lines += [text(vb,t.bold,bc)+l+text(vb,t.bold,bc)]
            r -= 1
        f = text((self.w-2)*self.f,t.bold,t.black)
        lines += r*[text(vb,t.bold,bc)+f+text(vb,t.bold,bc)]
        lines += [text(cb+hb*(self.w-2)+cb,t.bold,bc)]
        xfill = min(t.width -self.x,self.w)
        yfill = min(t.height-self.y,self.h)
        clip(t,self.x-x,self.y-y,lines,xfill,yfill)
        self.needdraw = False


class app(object):


    def abox(self,lines,x,y,w,h,**kws):
        b = box(self,lines,x,y,w,h,**kws)
        self.boxes.append(b)
        return b


    def __setattr__(self,k,v):
        if k == 'selected':
            if v == len(self.boxes):v = 1
            elif v == 0:v = len(self.boxes)-1
            if not self.selected is None:
                self.boxes[self.selected].selected = False
                self.boxes[self.selected].needdraw = True
            self.boxes[v].selected = True
            self.boxes[v].needdraw = True
        object.__setattr__(self,k,v)


    def __init__(self,t,x = 0,y = 0,bg = '*',timeout = 0.1,selected = None):
        self.t = t
        self.x = x
        self.y = y
        self.timeout = timeout
        object.__setattr__(self,'selected',selected)
        self.boxes = []
        self.bg = self.abox([],0,0,None,None,f = bg,fixed = True)
        self.needdraw = self.needbgdraw = True
        def on_resize(sig,action):
            for b in self.boxes:b.needdraw = True
            self.needdraw = self.needbgdraw = True
        signal.signal(signal.SIGWINCH,on_resize)


    def run(self,exit = False):
        if self.selected is None:
            self.selected = len(self.boxes)-1
        with self.t.fullscreen():
            with self.t.hidden_cursor():
                self.bg.print(self.t,self.x,self.y)
                while not exit:
                    exit = self.loop()


    def pan(self,dx,dy):
        if dx < 0 and self.x < 1:return
        if dy < 0 and self.y < 1:return
        self.x += dx
        self.y += dy
        self.x = max(0,self.x)
        self.y = max(0,self.y)
        self.needdraw = self.needbgdraw = True
        for b in self.boxes:b.needdraw = True


    def loop(self):
        reserved = ('','[',']')
        for b in self.boxes:
            if b.callback:
                b.callback(b)
        self.draw()
        with self.t.cbreak():
            key = self.t.inkey(timeout = self.timeout)
            sb = self.boxes[self.selected]
            if not key in reserved and not sb.inkey is None:
                key = sb.inkey(sb,key)
            if   key == 'j':self.pan(0,1)
            elif key == 'k':self.pan(0,-1)
            elif key == 'h':self.pan(-1,0)
            elif key == 'l':self.pan(1,0)
            elif key == '[':self.selected -= 1
            elif key == ']':self.selected += 1
            elif key == 'q':return True
        return False


    def draw(self):
        if self.needbgdraw:
            self.bg.print(self.t,self.x,self.y)
        if self.needdraw:
            for b in self.boxes:
                if b.needdraw and not b.selected:
                    b.print(self.t,self.x,self.y)
            sb = self.boxes[self.selected]
            if sb.needdraw:
                sb.print(self.t,self.x,self.y)
        #border(self.t,('#','#','#'))
        self.needdraw = self.needbgdraw = False


def main():
    t = blessed.Terminal()
    a = app(t)

    head = a.abox(['blah','blah','blah'],0,0,None,   5,anchor = (-1,-1))
    body = a.abox(['blah','blah','blah'],0,0,None,None,anchor = (-1, 0),maxh = -10)
    tail = a.abox(['blah','blah','blah'],0,0,None,   5,anchor = (-1, 1))

    a.run()


def anchortest():
    t = blessed.Terminal()
    a = app(t)
    ul = a.abox(3*['abc'],0,0,5,5,anchor = (-1,-1))
    uc = a.abox(3*['abc'],0,0,5,5,anchor = ( 0,-1))
    ur = a.abox(3*['abc'],0,0,5,5,anchor = ( 1,-1))
    cl = a.abox(3*['abc'],0,0,5,5,anchor = (-1, 0))
    cc = a.abox(3*['abc'],0,0,5,5,anchor = ( 0, 0))
    cr = a.abox(3*['abc'],0,0,5,5,anchor = ( 1, 0))
    ll = a.abox(3*['abc'],0,0,5,5,anchor = (-1, 1))
    lc = a.abox(3*['abc'],0,0,5,5,anchor = ( 0, 1))
    lr = a.abox(3*['abc'],0,0,5,5,anchor = ( 1, 1))
    a.run()


def demo():
    t = blessed.Terminal()
    a = app(t)
    ###

    def inp(b,key):
        return key

    def cb(b):
        if b.content[0] == 'but...':
            b.content = 5*['merrick...']
        elif b.content[0] == 'merrick...':
            b.content = 5*['garland...']
        elif b.content[0] == 'garland...':
            b.content = 5*['but...']
        b.app.needdraw = b.needdraw = True

    b = a.abox(5*['but...'],50,4,40,30,cb = cb,inkey = inp)

    b = a.abox(5*[text('but...',t.red,t.bold)],2,4,8,30)

    b = a.abox(20*[text('merrick...',t.blue,t.italic)],10,20,50,30)

    b = a.abox(10*[text('garland...')],30,40,50,30)

    ###
    a.run()


if __name__ == '__main__':
    #anchortest()
    main()
