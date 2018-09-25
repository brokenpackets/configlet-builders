import jsonrpclib
from cvplibrary import Form
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

"""
Instructions:
   - Create static configlet with all interface-level configuration.
      eg: 
          description Host-Uplink
          switchport
          switchport mode trunk
          switchport trunk native vlan 200
          switchport trunk allowed vlan 200,300,400
          spanning-tree portfast
          spanning-tree bpduguard enable

   - Rename user variable 'configlet' to match configlet name.
   - Rename user variable 'cvpserver' to match CVP server fqdn.
   - Create configlet to assign host-facing interfaces the comment "Dyn_intf = Compute_INTF_Config"
       and apply to all devices that those interfaces should apply to.
      eg:
          interface Ethernet1
            !! Dyn_intf = Compute_INTF_Config
   - Apply configlet to container - if any new VLANs are added, remove configlet and re-add.
"""

### User variables
cvpserver = 'localhost'
configlet = 'Compute_INTF_Config'

### Rest of script
restcall = 'https://'+cvpserver+':443//cvpservice/configlet/getConfigletByName.do?name='+configlet
vlanList = []
intf_regex = re.compile('interface .*')
intf_comment_regex = re.compile('Dyn_intf = '+configlet)
vlanIPAddrRegex = re.compile('^.*?\,([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\/[0-9]{1,2})')

def main():
  # Runs API call to grab configlet
  client = RestClient(restcall,'GET')
  if client.connect():
    # Parses configlet data into JSON.
    configletData = json.loads(client.getResponse())['config']
    # Splits configlet into list, divided at \n
    configList = configletData.split('\n')
   
  #SESSION SETUP FOR eAPI TO DEVICE
  url = "https://%s:%s@%s/command-api" % (user, passwd, ip)
  ss = jsonrpclib.Server(url)
  #CONNECT TO DEVICE
  runningconfig = ss.runCmds(1,['show running-config'])[0]['cmds']
  keylist = [x for x in runningconfig.keys() if intf_regex.match(x)]
  for item in keylist:
    # Loop over item comments
    for value in runningconfig[item]['comments']:
      # match comment against intf_comment_regex
      if intf_comment_regex.match(value):
        print item
        for configItem in configList:
          print '   '+configItem
        print '!'

if __name__ == "__main__":
    main()
