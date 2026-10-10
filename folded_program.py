"""Build current weekly folded programs inside the encrypted site payload."""
import base64, datetime, io, os, re
from xml.sax.saxutils import escape
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
import qrcode

BASE=os.path.dirname(os.path.abspath(__file__))
URL_RX=re.compile(r'https?://[^\s<>]+')

def complete(p):
    fields=('presiding','conducting','organist','chorister','invocation','benediction')
    if not all(p.get(k,'').strip() for k in fields): return False
    if any(re.search(r'placeholder|filler|tbd|test',p.get(k,''),re.I) for k in fields):return False
    if not all(p.get(k) and p[k].get('number') and p[k].get('title') for k in ('opening_hymn','sacrament_hymn','closing_hymn')): return False
    if not p.get('program_order'): return False
    m=p.get('musical_number')
    return not m or bool(m.get('song') and m.get('singers'))

def build(p,data,pin):
    draft=not complete(p)
    for name,path in [('Serif','/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'),('Sans','/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'),('SansBold','/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf')]:
        if name not in pdfmetrics.getRegisteredFontNames():
            if not os.path.exists(path):path=path.replace('/liberation/','/liberation2/')
            pdfmetrics.registerFont(TTFont(name,path))
    NAVY=HexColor('#203751');GOLD=HexColor('#9D8347');INK=HexColor('#26323B');MUTED=HexColor('#58636B');RULE=HexColor('#DDE4E7')
    W,H,CW,IN=792,612,396,36;PW=CW-2*IN
    day=datetime.date.fromisoformat(p['date']);label=day.strftime('%B %-d, %Y');end=day+datetime.timedelta(days=6)
    out=io.BytesIO();c=canvas.Canvas(out,pagesize=(W,H),pageCompression=1,invariant=1);c.setTitle('Milton Ward folded program - '+label);c.setAuthor('Milton Ward')
    body=ParagraphStyle('body',fontName='Sans',fontSize=9.3,leading=12,textColor=INK)
    def para(x,y,text,width=PW,style=body,gap=4):
        obj=Paragraph(text,style);_,h=obj.wrap(width,600);obj.drawOn(c,x+IN,y-h);return y-h-gap
    def title(x,y,text,kicker):
        c.setFillColor(GOLD);c.setFont('SansBold',8);c.drawString(x+IN,y,kicker.upper());y-=28
        c.setFillColor(NAVY);c.setFont('Serif',16);c.drawString(x+IN,y,text);y-=16;c.setStrokeColor(RULE);c.line(x+IN,y,x+CW-IN,y);return y-20
    def footer(x,text):
        c.setStrokeColor(RULE);c.line(x+IN,36,x+CW-IN,36);c.setFillColor(MUTED);c.setFont('Sans',7.4);c.drawString(x+IN,21,text)
    def crease():
        c.setStrokeColor(RULE);c.setDash(2,4);c.line(CW,18,CW,H-18);c.setDash()
    def pair(y,role,item,size=9.1):
        left=IN;right=CW-IN
        c.setFillColor(INK);c.setFont('Sans',size);c.drawString(left,y,role)
        available=PW-pdfmetrics.stringWidth(role,'Sans',size)-20
        fs=size
        while pdfmetrics.stringWidth(item,'SansBold',fs)>available and fs>8: fs-=.2
        if pdfmetrics.stringWidth(item,'SansBold',fs)>available: raise ValueError('Agenda value exceeds printable width: '+role)
        c.setFont('SansBold',fs);c.drawRightString(right,y,item)
        a=left+pdfmetrics.stringWidth(role,'Sans',size)+9;b=right-pdfmetrics.stringWidth(item,'SansBold',fs)-9
        if b>a+9:
            c.setStrokeColor(MUTED);c.setDash(1,2.6);c.setLineWidth(.5);c.line(a,y-1.6,b,y-1.6);c.setDash()
    def hymn(h): return 'No. '+h['number']+' · '+h['title']
    crease();c.setFillColor(MUTED);c.setFont('Sans',8);c.drawString(IN,H-49,'NOTES / MISSIONARY ADDRESSES')
    for y in range(H-84,70,-33): c.setStrokeColor(RULE);c.line(IN,y,CW-IN,y)
    footer(0,'');x=CW
    c.setFillColor(NAVY);c.setFont('Serif',26);c.drawCentredString(x+CW/2,535,'Milton Ward')
    c.setStrokeColor(GOLD);c.setLineWidth(.8);c.line(x+119,515,x+CW-119,515)
    c.setFillColor(MUTED);c.setFont('Sans',9);c.drawCentredString(x+CW/2,491,'SUNDAY, '+label.upper())
    imagepath=os.path.join('/tmp','ward-good-shepherd.jpg')
    if not os.path.exists(imagepath):
        import urllib.request
        urllib.request.urlretrieve('https://www.churchofjesuschrist.org/imgs/75e126dbc032d0810fc934018c5ca415116ce5cb/full/1920%2C/0/default',imagepath)
    image=ImageReader(imagepath);iw,ih=image.getSize();dw=300;dh=dw*ih/iw;bottom=155+(312-dh)/2
    c.drawImage(image,x+(CW-dw)/2,bottom,width=dw,height=dh)
    c.setFont('Sans',7.4);c.drawCentredString(x+CW/2,bottom-15,'The Good Shepherd');c.drawCentredString(x+CW/2,bottom-26,'Del Parson')
    footer(x,'WORKING DRAFT - PRAYERS NOT YET SET' if draft else 'SACRAMENT MEETING PROGRAM');c.showPage();crease()
    y=title(0,H-40,'Sacrament meeting','Sunday, '+label)
    for role,k in [('Presiding','presiding'),('Conducting','conducting'),('Organist','organist'),('Chorister','chorister')]: pair(y,role,p[k],9.8);y-=15.5
    y-=14
    agenda=[('Opening hymn',hymn(p['opening_hymn'])),('Invocation',p.get('invocation','') or '____________________'),('Sacrament hymn',hymn(p['sacrament_hymn'])),('', 'Administration of the Sacrament')]
    for a in p['program_order']:
        if a['type']=='speaker': agenda.append(('' if a['name'].lower()=='bishop comments' else 'Speaker',a['name']))
        elif a['type']=='hymn': agenda.append(('Intermediate hymn',hymn(a['hymn'])))
        elif a['type']=='musical_number': agenda.append(('Musical number',a['song']));agenda.append(('Performed by',a['singers']))
    agenda.extend([('Closing hymn',hymn(p['closing_hymn'])),('Benediction',p.get('benediction','') or '____________________')])
    for role,item in agenda:
        if role: pair(y,role,item);y-=24
        else: y-=10;c.setFillColor(MUTED);c.setFont('Sans',9.2);c.drawCentredString(CW/2,y,item);y-=24
    if y<47: raise ValueError('Agenda exceeds printable page')
    footer(0,'WORKING DRAFT - PRAYERS NOT YET SET' if draft else '');x=CW;y=title(x,H-40,'Announcements',day.strftime('%B %-d')+'-'+str(end.day)+' & upcoming')
    def sub(y,text):
        c.setFillColor(NAVY);c.setFont('SansBold',9);c.drawString(x+IN,y,text.upper());return y-13
    def qrrow(y,text,url,caption):
        q=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,box_size=12,border=4);q.add_data(url);q.make(fit=True)
        img=io.BytesIO();q.make_image(fill_color='black',back_color='white').save(img,format='PNG');img.seek(0)
        size=70;yp=para(x,y,text,width=PW-size-9,gap=0);c.drawImage(ImageReader(img),x+CW-IN-size,y-size,width=size,height=size)
        sty=ParagraphStyle('label',parent=body,fontName='SansBold',fontSize=8,leading=9.5,alignment=1,textColor=NAVY)
        obj=Paragraph(escape(caption),sty);_,lh=obj.wrap(size,100);obj.drawOn(c,x+CW-IN-size,y-size-3-lh)
        return min(yp,y-size-3-lh)-3
    y=qrrow(y,'<b>Milton Ward online</b><br/>Scan for programs, announcements and youth activities.<br/>miltonward.com<br/>PIN: <b>'+escape(pin)+'</b> (case-sensitive).','https://miltonward.com','Ward website')
    y=sub(y,'This week')
    for a in p.get('announcements',[]):
        t=a.get('text','')
        if t and 'trunk or treat' not in t.lower() and 'online program' not in t.lower(): y=para(x,y,escape(t),gap=4)
    for a in (data.get('activities') or {}).get('rows',[]):
        if p['date']<=a['date']<=end.isoformat():
            ad=datetime.date.fromisoformat(a['date']);text=a.get('reference') or a.get('schedule') or ''
            if text:y=para(x,y,'<b>'+ad.strftime('%a, %B %-d')+':</b> '+escape(text)+'.',gap=4)
    if p['date']=='2026-10-11': y=para(x,y,'<b>Sat, October 17:</b> Corn maze for all youth.',gap=14)
    # Only scoped public announcements; exclude examples, ended events and weekly duplicate corn maze.
    from prune import is_stale
    for sec in data.get('announcement_sections',[]):
        items=[t for t in sec['items'] if not t.lower().startswith(('example:','milton ward online:')) and not is_stale(t,day) and not (p['date']=='2026-10-11' and 'corn maze' in t.lower())]
        if not items:continue
        y=sub(y,sec['header'].replace(' Announcements',''))
        for t in items:
            urls=URL_RX.findall(t)
            clean=URL_RX.sub('',t).strip()
            if 'Halloween Trunk or Treat' in clean:
                clean='Halloween Trunk or Treat: Friday, October 30, 6:00-8:00 PM at Hunter Tree Farm, 14680 Wood Road. Chili, costume and trunk contests; wagon rides.'
            elif 'Logo contest for the new Shipp Family Camp' in clean:
                clean='Shipp Family Camp logo contest: Youth and adults may submit designs by November 15, 2026.'
            elif 'All Stake Family members ages 8' in clean:
                clean='Ages 8+ may sing two numbers at Conference; see President Brom’s email or a ward clerk to sign up.'
            elif 'Save the dates for stake Young Men camp' in clean:
                clean='July 14-17, 2027: Roswell Stake Young Men camp. New location and details to follow.'
            clean=re.sub(r'(?:Sign up:|Guidelines and submission form:)\s*$', '',clean,flags=re.I).strip()
            if urls:
                name='Trunk or Treat sign-up' if 'trunk' in t.lower() else 'Camp logo submission form' if 'logo contest' in t.lower() else sec['header']+' link'
                y=qrrow(y,escape(clean),urls[0],name)
                for j,url in enumerate(urls[1:],2):y=qrrow(y,'',url,name+' '+str(j))
            else:y=para(x,y,escape(clean),gap=4)
    if y<47:raise ValueError('Announcements exceed printable page: '+str(y))
    footer(x,'');c.save();return out.getvalue()

def program_fingerprint(p,data):
    import hashlib,json
    return hashlib.sha256(json.dumps({'program':p,'announcements':data.get('announcement_sections',[]),'activities':data.get('activities')},sort_keys=True).encode()).hexdigest()

def add_printable(data,pin):
    # Previous generated PDFs remain encrypted; do not invent historic announcement snapshots.
    pdfs={}
    old=os.path.join(BASE,'data.enc')
    if os.path.exists(old):
        try:
            import hashlib,json
            from cryptography.hazmat.primitives.ciphers import Cipher,algorithms,modes
            from cryptography.hazmat.primitives import padding
            b=open(old,'rb').read();key=hashlib.pbkdf2_hmac('sha256',pin.encode(),b[:16],100000,32);dec=Cipher(algorithms.AES(key),modes.CBC(b[16:32])).decryptor();raw=dec.update(b[32:])+dec.finalize();u=padding.PKCS7(128).unpadder();prior=json.loads(u.update(raw)+u.finalize());pdfs=prior.get('printable_programs',{})
        except Exception as e:raise ValueError('Cannot preserve existing encrypted PDFs') from e
    future=[p for p in data['programs'] if p['date']>='2026-10-11']
    if future:
        p=max(future,key=lambda q:q['date'])
        # Publish source changes immediately, including visibly unfinished drafts.
        if all(p.get(k) and p[k].get('number') and p[k].get('title') for k in ('opening_hymn','sacrament_hymn','closing_hymn')) and p.get('program_order'):
            try:pdfs[p['date']]=base64.b64encode(build(p,data,pin)).decode()
            except ValueError as e:
                pdfs.pop(p['date'],None)
                print('PRINTABLE REVIEW REQUIRED:',p['date'],e)
        else: pdfs.pop(p['date'],None)
    data['printable_programs']=pdfs
