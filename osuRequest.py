# This Python file uses the following encoding: utf-8
import requests
import json
import time
import io
import pymongo
import math
apiURL = 'http://osu.ppy.sh/api'
apiKey = ''
while(apiKey==''): apiKey=input('Need apiKey!')
weekConstant = 7*24*60*60
client = pymongo.MongoClient()
db = client.osu
users = db.users
diffs = db.diffs
mod = dict(
	Nomod           = 0,
	NoFail         = 1,
	Easy           = 2,
	NoVideo      = 4,
	Hidden         = 8,
	HardRock       = 16,
	SuddenDeath    = 32,
	DoubleTime     = 64,
	Relax          = 128,
	HalfTime       = 256,
	Nightcore      = 512, 
	Flashlight     = 1024,
	Autoplay       = 2048,
	SpunOut        = 4096,
	Relax2         = 8192,	
	Perfect        = 16384
)
def getBP(user):
    payload = { 'k':apiKey, 'u':user, 'm':0 , 'limit':100 }
    r = requests.get(apiURL+'/get_user_best' ,params = payload )
    return r.text
    
def getRecentBP(user):
    data = json.loads( getBP(user) )
    currentTime = int( time.mktime( time.localtime() ))
    pattern = '%Y-%m-%d %H:%M:%S'
    output = io.StringIO()
    countBP = 0
    for bpRecord in data:
        convertBPTime = int( time.mktime( time.strptime(bpRecord['date'],pattern) ) ) 
        if(currentTime - convertBPTime < weekConstant):
            countBP = countBP + 1
            if(countBP>10):
                break
            output.write( getMAPName( bpRecord['beatmap_id'] )+'\n' )
            output.write( 'MapLink is http://osu.ppy.sh/b/' + bpRecord['beatmap_id'] + '\n' )
            output.write( user + ' farmed ' + bpRecord['pp'] + 'pp from this map on ' + bpRecord['date'] + '\n' )
            output.write( '--------\n')
    result = output.getvalue()
    output.close()
    return result

def getMAP(mapid):
    payload = { 'k':apiKey, 'b':mapid, 'm':0 }
    r = requests.get(apiURL+'/get_beatmaps', params = payload)
    return r.text

def getMAPName(mapid):
    data = json.loads(getMAP(mapid)).pop()
    return data['artist'] + '-' + data['title'] + '\n' + 'Created by ' + data['creator'] + ', diff = ' + data['difficultyrating'][:4]

def getMods(num):
    mods = ''
    for i in mod:
        if(num & mod[i] > 0):
            mods = mods + i + ' '
    if(num==0):
        mods = 'No'
    return mods

def getACC(rec):
    s300 = float(rec['count300'])
    s100 = float(rec['count100'])
    s50 = float(rec['count50'])
    misses = float(rec['countmiss'])
    return str(((300*s300 + 100*s100+50*s50)/(300*(s300+s100+s50+misses))*100))[:5]
    
def getHistory(user):
    payload = { 'k':apiKey, 'u':user, 'm':0 , 'limit':50 }
    r = requests.get(apiURL+'/get_user_recent' ,params = payload )
    playList = json.loads(r.text)
    res = ''
    mapDict = {}
    for i in playList:
        #map = json.loads(i['beatmap_id']).pop()
        if(not i['beatmap_id'] in mapDict):
            mapDict.update({i['beatmap_id']:i})
        else:
            if( int(i['score'])> int(mapDict[ i['beatmap_id'] ][ 'score' ])):
                mapDict.update({i['beatmap_id']:i})
                
    for id in mapDict:
        map = json.loads(getMAP(id)).pop()
        slot = mapDict[id]
        rec = user + '在{mapName}[{diff}]({star}☆)中使用了{mods}mod，成绩评级为{rate},combo数为{cb}/{maxcb}。得分为{sc},ACC为{acc}%,{s300}/{s100}/{s50}/{misses}\n'.format(
        mapName = map['title'],
        star = map['difficultyrating'][:5],
        diff = map ['version'],
        mods = getMods(int(slot['enabled_mods'])),
        rate = slot['rank'],
        cb = slot['maxcombo'],
        maxcb = map['max_combo'],
        sc = slot['score'],
        acc = getACC(slot),
        s300 = slot['count300'],
        s100 = slot['count100'],
        s50 = slot['count50'],
        misses = slot['countmiss']
        )
        res = res + rec
    return res    
    
def getPP(username):
    #try:
    res = (users.find_one({'username':username}))
    if(res!=None): return res['pp']
    #except valueError: return
    time.sleep(0.1)
    payload = { 'k':apiKey, 'u':username }
    #print (username)
    r = requests.get(apiURL+'/get_user' ,params = payload )
    pp = float(json.loads(r.text).pop()['pp_raw'])
    users.insert_one({'username':username,'pp':pp})
    print('new user {us}'.format(us=username))
    return pp
def getTop100(id):
    res = (diffs.find_one({'id':id}))
    if(res!=None): return res['blind']
    payload = { 'k':apiKey, 'b':id, 'limit':100 }
    r = requests.get(apiURL+'/get_scores' ,params = payload )
    rankData = json.loads(r.text)
    map = json.loads(getMAP(id)).pop()
    diff = float(map['difficultyrating'])
    if(diff<4 or int(map['passcount'])<4500): return 'Too easy or not enough playcount'
    max_combo = int(map['max_combo'])
    ans=0
    for i in rankData:
        #print(i)
        
        mods = (getMods(int(i['enabled_mods'])))
        modFactor = 1.0
        if(mods.find('Hid')!=-1): modFactor/=1.1
        if(mods.find('Doub')!=-1): modFactor/=2
        if(mods.find('Hard')!=-1): modFactor/=1.4
        if(mods.find('Flash')!=-1): modFactor/=1.5
        if(mods.find('Easy')!=-1): modFactor *=1.4
        if(mods.find('HalfTime')!=-1): modFactor*=1.6
        modFactor = math.pow(modFactor,2)
        
        ppFactor = getPP(i['user_id'])
        comboFactor = math.pow(max_combo/int(i['maxcombo']),0.5)
        accFactor = 1/math.pow( float(getACC(i))/100, 1.6)
        ans+=modFactor*(1+diff/10)*(10+ppFactor/100)*comboFactor/2500*accFactor
        
    ans = math.pow(ans,0.8)*2.1
    diffs.insert_one({'song':map['title'],'blind':ans,'diff':diff,'id':id})
    print(ans)
  
#def getBlind(combo,    
while(1):
    beatmapid = input()
    getTop100(beatmapid)
#print(getPP('rafis'))
#print( getRecentBP('luffyty') ) for debug
