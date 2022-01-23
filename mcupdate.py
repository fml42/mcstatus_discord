import aiohttp
import asyncio
import mcstatus
import urllib
import traceback
import re

##########################################
#   config 
##########################################

mc_ip               = "localhost:25565"
#minecraft server address or ip. format: 'ip:port'

update_interval     = 600
#10 minutes. discord rate limits renaming channels to twice every 10 minutes

channel_id          = 000000000000000000
#channel id of the channel to be updated

name_template       = "mc {version} | {playercount}/{maxplayers}"
# will replace '{playercount}', '{maxplayers}' and '{version}' accordingly

token               = "000000000000000000000000.000000.000000000000000000000000000"
#discord bot token. bot must be able to see + have manage channels (permission integer: 16) permissions on the channel it should update.

discord_api_url     = "https://discord.com/api/v9/"
#only change this if api version changes.

##########################################

async def rename_channel(session, channel, name, audit_reason=""):
    async with session.patch(f"{discord_api_url}channels/{channel}", json = {
            "name" : name,
        }, headers = { 
            "Authorization" : f"Bot {token}",
            "X-Audit-Log-Reason" : urllib.parse.quote(audit_reason),
        }) as r:
            try:
                return (r.status, await r.json())
            except:
                return (r.status, None)
    
async def mc_update_loop():
    async with aiohttp.ClientSession() as session:
        mcserver = mcstatus.MinecraftServer.lookup(mc_ip)
        last_name = None
        while 1:
            retry_after = 0
            print("[mcupdate] fetching minecraft status update")
            try:
                mcst = None
                try:
                    mcst = mcserver.status()
                except Exception as e2:
                    print(f"[mcupdate] could not get mc status: {e2}")
                if mcst:
                    if mcst.players:
                        online = mcst.players.online
                        online_max = mcst.players.max
                        version = ""
                        try:
                            version = re.search(r'[\.\d]+', mcst.version.name).group(0)
                        except:
                            print(f"[mcupdate] could not determine version from string '{mcst.version.name}'")
                    
                        print(f"[mcupdate] online={online}/{online_max}, version={version}")
                    
                        text = name_template
                        text = text.replace("{playercount}", str(online))
                        text = text.replace("{maxplayers}", str(online_max))
                        text = text.replace("{version}", version)
                        
                        if text != last_name:
                            status_code, resp = await rename_channel(session, channel_id, text)
                            if status_code == 200:
                                print(f"[mcupdate] updated channel name to: {text}")
                                last_name = text
                            elif status_code == 429 and resp:
                                retry_after = resp['retry_after']
                                print(f"[mcupdate] rate limited. retry after: {retry_after}")
                            else:
                                print(f"[mcupdate] unexpected http status code: {status_code}")
                        else:
                            print("[mcupdate] name did not change, not updating")
                        
            except Exception as e:
                print(f"[mcupdate] minecraft update error: {e}")
                traceback.print_exc()
                
            await asyncio.sleep(max(update_interval, retry_after))
        
        
if __name__ == "__main__":
    asyncio.run(mc_update_loop())