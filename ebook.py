from debug import LOG
from struct import unpack,pack,calcsize

MOBIHEADER_FMT = ">4s4I48x2I"
'''
http://wiki.mobileread.com/wiki/MOBI#Format

4s - MOBI
I - hlen
I - type
I - encoding
I - UID
48x - (I+40x+I) generator version + reserved + 1st non-book index
I - full name offset
I - full name length
I - locale
32x - 4I + 16x - uninteresting stuff
I - EXTH flags
32x - unknown
16x - 4I drm stuff
'''
            
EXTH_FMT = ">4x2I"
'''4x = "EXTH", I = hlen, I = record count'''

EXTH_RECORD_TYPES = {
        1 : 'drm server id',
        2 : 'drm commerce id',
        3 : 'drm ebookbase book id',
        100 : 'author',
        101 : 'publisher',
        102 : 'imprint',
        103 : 'description',
        104 : 'isbn',
        105 : 'subject',
        106 : 'publishingdate',
        107 : 'review',
        108 : 'contributor',
        109 : 'rights',
        110 : 'subjectcode',
        111 : 'type',
        112 : 'source',
        113 : 'asin',
        114 : 'version number',
        115 : 'sample',
        116 : 'start reading',
        118 : 'retail price',
        119 : 'retail price currency',
        201 : 'cover offset',
        202 : 'thumbnail offset',
        203 : 'has fake cover',
        208 : 'watermark',
        209 : 'tamper proof keys',
        401 : 'clipping limit',
        402 : 'publisher limit',
        404 : 'ttsflag',
        502 : 'cde type',
        503 : 'updated title'
        }

def parse_palmdb(data):
    from PalmDB import PalmDatabase
    db = PalmDatabase.PalmDatabase()
    db.fromByteArray(data)
    return db

def read(fn):
    d = open(fn).read()
    encodings = {
            1252: 'cp1252',
            65001: 'utf-8'
            }
    supported_types = ('BOOKMOBI','TEXtREAd')
    ptype = d[60:68]
    if ptype not in supported_types:
        LOG(1,"Unsupported file type %s" % (ptype))
        return None

    db = parse_palmdb(d) 
    rec0 = db.records[0].toByteArray(0)[1]
    
    #LOG(5,repr(rec0))
    if ptype == 'BOOKMOBI':
        LOG(3,"This is a MOBI book")
        id, hlen, mobitype, encoding, uid, nameoffs, namelen = unpack(
                MOBIHEADER_FMT, rec0[16:16+calcsize(MOBIHEADER_FMT)])
        LOG(3,
        "id: %s, hlen %d, type %d, encoding %d, uid %d, offset %d, len %d" %
        (id, hlen, mobitype, encoding, uid, nameoffs, namelen))

        # Get and decode the book name
        name = rec0[nameoffs:nameoffs+namelen].decode(encodings[encoding])

        LOG(3,"Book name: %s" % name)
        if id != 'MOBI':
            LOG(0,"Mobi header missing!")
        if (0x40 & unpack(">I",rec0[128:132])[0]): # check for EXTH
            exth = parse_exth(rec0,hlen+16)

    elif ptype == 'TEXtREAd':
        LOG(2,"This is an older MOBI book")

def parse_exth(data,pos):
    ret = {}
    n = 0
    if (pos != data.find('EXTH')):
        LOG(0,"EXTH header not found where it should be @%d" % pos)
        return None
    else:
        end = pos+calcsize(EXTH_FMT)
        (hlen, count) = unpack(EXTH_FMT, data[pos:end])
        LOG(3,"pos: %d, EXTH header len: %d, record count: %d" % (
            pos, hlen, count ))
        pos = end
        while n < count:
            end = pos+calcsize(">2I")
            t,l = unpack(">2I",data[pos:end])
            v = data[end:pos+l]
            if l-8 == 4:
                v = unpack(">I",v)[0]
            if t in EXTH_RECORD_TYPES:
                LOG(2,"EXTH record '%s' @%d+%d: '%s'" % (
                    EXTH_RECORD_TYPES[t], pos, l-8, v))
                ret[t] = v
            else:
                LOG(3,"Found an unknown EXTH record type %d @%d+%d: '%s'" %
                        (t,pos,l-8,repr(v)))
            pos +=l
            n += 1
    return ret
