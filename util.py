# coding: utf-8
import tornado.template
from Crypto.Cipher import AES
import base64

import os
import psycopg2
import urlparse

def read_static_page(page_name):
    res = ""
    page = open(page_name, 'r')
    for line in page.readlines():
        res += line
    return res

def read_page(page_name, **kwargs):
    loader = tornado.template.Loader("static/html/")
    return loader.load(page_name).generate(**kwargs)



SMILEYS = [":)",":snif:",":gba:",":g)",":-)",":snif2:",":bravo:",":d)",":hap:",":ouch:",":pacg:",":cd:",
":-)))",":ouch2:",":pacd:",":cute:",":content:",":p)",":-p",":noel:",":oui:",":(",":peur:",":question:",
":cool:",":-(",":coeur:",":mort:",":rire:",":-((",":fou:",":sleep:",":-D",":nonnon:",":fier:",":honte:",
":rire2:",":non2:",":sarcastic:",":monoeil:",":o))",":nah:",":doute:",":rouge:",":ok:",":non:",":malade:",":fete:",
":sournois:",":hum:",":ange:",":diable:",":gni:",":play:",":desole:",":spoiler:",":merci:",":svp:",":sors:",":salut:",
":rechercher:",":hello:",":up:",":bye:",":gne:",":lol:",":dpdr:",":dehors:",":hs:",":banzai:",":bave:",":pf:",":cimer:",
":ddb:",":pave:",":objection:",":siffle:"]

def replace_smiley(text):
    for i in xrange(len(SMILEYS)-1,-1,-1):
        text = text.replace(SMILEYS[i],"<img src='/static/images/smileys/" + str(i+1) + ".gif'/>")
    text = text.replace(":pls:","<img src='/static/images/smileys/pls.png' style='width: 40px; height: 40px'/>")
    return text


#DB
passcrypt = "FAsrtdltfFE5rTVrlay6Vtc5"

#urlparse.uses_netloc.append("postgres")
#url = urlparse.urlparse(os.environ["DATABASE_URL"])



def openDB():
    return psycopg2.connect(
        database=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port
    )

def encrypt(password):
    encryption = AES.new(passcrypt, AES.MODE_CBC, 'This is an IV456')
    password += "a"*(16-len(password)%16)
    return base64.b64encode(encryption.encrypt(password))

def compare(crypted_password, password):
    encryption = AES.new(passcrypt, AES.MODE_CBC, 'This is an IV456')
    p = str(password + "a"*(16-len(password)%16))
    dp = encryption.decrypt(base64.b64decode(crypted_password))
    print p
    print dp
    return dp == p


def add_player(pseudo, password):
    pseudo = pseudo.lower()
    db = openDB()
    query = db.cursor()
    query.execute('INSERT INTO Players (Pseudo, Password, Type, Score) VALUES (%s,%s,%s,%s)',(pseudo, encrypt(password), 0, 500))
    db.commit()
    query.close()
    db.close()

def check_pseudo(pseudo):
    pseudo = pseudo.lower()
    db = openDB()
    query = db.cursor()
    query.execute('SELECT * FROM Players WHERE Pseudo=%s',(pseudo,))
    pl = query.fetchone()
    res = pl == None
    query.close()
    db.close()
    return res

def check_player(pseudo, password):
    pseudo = pseudo.lower()
    res = 0
    t = -1
    db = openDB()
    query = db.cursor()
    query.execute('SELECT * FROM Players WHERE Pseudo=%s',(pseudo,))
    pl = query.fetchone()
    print pl
    if(pl == None):
        res = -1
    elif not compare(pl[2], password):
        res = -2
    else:
        t = int(pl[3])
    query.close()
    db.close()
    return res, t

