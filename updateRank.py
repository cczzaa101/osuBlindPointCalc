import requests
import re
import pymongo
import time
client = pymongo.MongoClient()
db = client.osu
users = db.users
diffs = db.diffs
fakeHeader = {
'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36'
}


def getPP(rawText):
    time.sleep(0.1)
    userlist =  (re.findall(r'/u/(\d*?)"',rawText,re.S))
    pplist = (re.findall(r'bold.\>(.*?)pp',rawText,re.S))
    if(len(pplist)!=len(userlist) and len(pplist)!=50):
        return('incomplete page!')
        #input()
    for i in range(50):
        res = (users.find_one({'username':userlist[i]}))
        if(res==None): 
            users.insert_one({'username':userlist[i],'pp':float(pplist[i].replace(',',''))})
            
    return 'success!'

for i in range(200):
    payload = {
    'm':0,
    's':3,
    'o':1,
    'f':'',
    'page':i+1,
    }
    print(getPP(requests.get('https://osu.ppy.sh/p/pp/', params = payload, headers = fakeHeader).text))
