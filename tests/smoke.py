#!/usr/bin/env python3
import argparse, json, subprocess
ap=argparse.ArgumentParser()
ap.add_argument('command')
ap.add_argument('server_name')
ap.add_argument('--grid-rows',type=int,default=4)
ap.add_argument('--grid-cols',type=int,default=6)
ns=ap.parse_args()
p=subprocess.Popen([ns.command],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
def rpc(i,m,params=None):
    p.stdin.write(json.dumps({'jsonrpc':'2.0','id':i,'method':m,'params':params or {}})+'\n'); p.stdin.flush()
    return json.loads(p.stdout.readline())
r=rpc(1,'initialize',{'protocolVersion':'2025-06-18','capabilities':{},'clientInfo':{'name':'smoke','version':'1'}})
assert r['result']['serverInfo']['name']==ns.server_name, r
r=rpc(2,'tools/list')
assert [t['name'] for t in r['result']['tools']]==['screenshot','click','mouse','keyboard'], r
r=rpc(3,'tools/call',{'name':'screenshot','arguments':{'grid_rows':ns.grid_rows,'grid_cols':ns.grid_cols}})
assert not r['result']['isError'], r
meta=json.loads(next(c['text'] for c in r['result']['content'] if c['type']=='text'))
img=next(c for c in r['result']['content'] if c['type']=='image')
assert meta['width']>0 and meta['height']>0 and len(img['data'])>1000
print('OK',ns.server_name,meta,'png_base64_chars',len(img['data']))
p.terminate()
