import json, os, urllib.request
ENDPOINT = "https://mcp.cloudflare.com/mcp"
headers = {"Authorization": "Bearer " + os.environ["CLOUDFLARE_MCP_TOKEN"], "Content-Type": "application/json", "Accept": "application/json, text/event-stream", "MCP-Protocol-Version": "2025-06-18"}
def send(body, notification=False):
    req=urllib.request.Request(ENDPOINT, data=json.dumps(body).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        sid=response.headers.get("mcp-session-id")
        if sid: headers["Mcp-Session-Id"]=sid
        raw=response.read(2000000).decode()
        if notification:return None
        if response.headers.get("content-type", "").startswith("text/event-stream"):
            for block in raw.split("\n\n"):
                data="\n".join(line[5:].strip() for line in block.splitlines() if line.startswith("data:"))
                if data:
                    value=json.loads(data)
                    if "id" in value:return value
        return json.loads(raw)
def embedded(value):
    if isinstance(value.get("structuredContent"),dict):return value["structuredContent"]
    for item in value.get("content",[]):
        if item.get("type")=="text":
            try:return json.loads(item["text"])
            except ValueError:pass
    return {}
send({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"offerte4zampe-fixed-build-readonly","version":"1.0"}}})
send({"jsonrpc":"2.0","method":"notifications/initialized"},True)
identity=embedded(send({"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"whoami","arguments":{}}}).get("result",{}))
identity=identity.get("result",identity)
account=identity.get("id","")
if account.startswith("account:"):account=account[8:]
else:account=os.environ.get("CLOUDFLARE_ACCOUNT_ID","")
if len(account)!=32 or any(c not in "0123456789abcdef" for c in account.lower()):raise SystemExit("Account could not be verified")
code=r"""async () => {
 const base="/accounts/"+accountId+"/builds/builds/96678e12-7991-44db-ac58-b7164c4822f1";
 const b=await cloudflare.request({method:"GET",path:base});
 const l=await cloudflare.request({method:"GET",path:base+"/logs"});
 const lines=Array.isArray(l?.result?.lines)?l.result.lines:[];
 const safe=lines.map(x=>Array.isArray(x)?x.filter(v=>typeof v==="string").join(" "):"").filter(s=>/error|fail|warn|denied|limit|unauth|cannot|could not|wrangler/i.test(s)).slice(-30).map(s=>/secret|password|api.key|bearer/i.test(s)?"[credential-related log line redacted]":s.replace(/https?:\/\/\S+/g,"[url]").replace(/[A-Za-z0-9_+\/=-]{30,}/g,"[long-value]").slice(0,350));
 return {build_readable:b?.success===true,logs_readable:l?.success===true,outcome:b?.result?.build_outcome||null,status:b?.result?.status||null,commit:b?.result?.build_trigger_metadata?.commit_hash||null,build_errors:b?.errors?.map(x=>({code:x.code,message:x.message}))||[],log_errors:l?.errors?.map(x=>({code:x.code,message:x.message}))||[],log_count:lines.length,truncated:l?.result?.truncated===true,safe_error_lines:safe};
}"""
result=send({"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"execute","arguments":{"code":code,"account_id":account}}})
data=embedded(result.get("result",{})); print(json.dumps(data))
