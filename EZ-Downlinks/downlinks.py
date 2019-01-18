import jsonrpclib
from cvplibrary import CVPGlobalVariables, GlobalVariableNames
from cvplibrary import RestClient
import json
import re
import ssl

# Ignore untrusted certificate for eAPI call.
ssl._create_default_https_context = ssl._create_unverified_context

#GET VARIABLES FROM CVP, USED TO AUTH TO DEVICE.
ip = CVPGlobalVariables.getValue(GlobalVariableNames.CVP_IP)
user = CVPGlobalVariables.getValue(GlobalVariableNames.CVP_USERNAME)
passwd = CVPGlobalVariables.getValue(GlobalVariableNames.CVP_PASSWORD)
cvpserver = 'localhost'

"""
Instructions:
   - Create static configlet(s) with all interface-level configuration.
      eg: 
          description Host-Uplink
          switchport
          switchport mode trunk
          switchport trunk native vlan 200
          switchport trunk allowed vlan 200,300,400
          spanning-tree portfast
          spanning-tree bpduguard enable
   - Create configlet to assign host-facing interfaces using a comment value of 
     "Dyn_intf = {configlet-name}" eg: "Dyn_intf = Compute_INTF_Config"
     and apply to all devices that those interfaces should apply to.
      eg:
          interface Ethernet1
            !! Dyn_intf = Compute_INTF_Config
   - Apply configlet to container - if any new VLANs are added, remove configlet and 
     re-add at container level.
"""

### Rest of script
def get_configlet(configlet):
  restcall = 'https://'+cvpserver+':443//cvpservice/configlet/getConfigletByName.do?name='+configlet
  # Runs API call to grab configlet
  client = RestClient(restcall,'GET')
  if client.connect():
    # Parses configlet data into JSON.
    configletData = json.loads(client.getResponse())['config']
    # Splits configlet into list, divided at \n
    configList = configletData.split('\n')
    return configList
vlanList = []
intf_regex = re.compile('interface Ethernet.*')
intf_comment_regex = re.compile('Dyn_intf = (.*)')

def main():
  #SESSION SETUP FOR eAPI TO DEVICE
  url = "https://%s:%s@%s/command-api" % (user, passwd, ip)
  ss = jsonrpclib.Server(url)
  #CONNECT TO DEVICE
  runningconfig = ss.runCmds(1,['show running-config'])[0]['cmds']
  keylist = [x for x in runningconfig.keys() if intf_regex.match(x)]
  for item in keylist:
    # Loop over item comments
    for comment in runningconfig[item]['comments']:
      # match comment against intf_comment_regex
      if intf_comment_regex.match(comment):
        configlet_name = intf_comment_regex.match(comment).group(1)
        configlet = get_configlet(configlet_name)
        print item
        for configItem in configlet:
          print '   '+configItem
        print '!'

if __name__ == "__main__":
    main()
