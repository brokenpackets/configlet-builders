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
   - Create static configlet with VLANID, Description, and anycast gateway IP per line, separated by a comma:
      eg: 5,DynVLAN5,192.168.5.1/24
          10,DynVLAN10,192.168.10.1/24
   - Rename user variable 'configlet' to match configlet name.
   - Rename user variable 'cvpserver' to match CVP server fqdn.
   - Apply configlet to container - if any new VLANs are added, remove configlet and re-add.
"""

### User variables
cvpserver = 'localhost'
configlet = 'Compute_VLANs'

### Rest of script
restcall = 'https://'+cvpserver+':443//cvpservice/configlet/getConfigletByName.do?name='+configlet
vlanList = []
vlanNumRegex = re.compile('^([0-9]{1,4})\,.*')
vlanNameRegex =  re.compile('^[0-9]{1,4}\,(.*)')
vlanIPAddrRegex = re.compile('^.*?\,([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\/[0-9]{1,2})')

def main():
  # Runs API call to grab configlet
  client = RestClient(restcall,'GET')
  if client.connect():
    # Parses configlet data into JSON.
    configletData = json.loads(client.getResponse())['config']
    # Splits configlet into list, divided at \n
    vlanList = configletData.split('\n')
   
  #SESSION SETUP FOR eAPI TO DEVICE
  url = "https://%s:%s@%s/command-api" % (user, passwd, ip)
  ss = jsonrpclib.Server(url)
  #CONNECT TO DEVICE
  response = ss.runCmds(1,['show ip bgp']) # run command 'show ip bgp' and store output as response.
  ASN =  response[0]['vrfs']['default']['asn'] # grab ASN from BGP JSON data.
  ROUTERID = response[0]['vrfs']['default']['routerId'] # grab Router-ID from BGP JSON data.

  allVlans = []
  #Create VLAN
  for vlan in vlanList:
    vlanId = vlanNumRegex.match(vlan).group(1)
    vlanName = vlanNameRegex.match(vlan).group(1)
    ipAddr = vlanIPAddrRegex.match(vlan).group(1)
    allVlans.append(vlanId)
    print 'vlan %s' % (vlanId)
    print ' name %s' % (vlanName)
    print '!'
    #Create VLAN Interface
    print 'interface Vlan %s' % (vlanId)
    print ' description %s' % (vlanName)
    print ' ip address virtual %s' % (ipAddr)
    print '!'
  #Assign VLAN to VNI
  print 'interface vxlan1'
  for vlan in allVlans:
    print '  vxlan vlan '+vlan+' vni '+vlan
  print '!'
  #Create MACVRF for EVPN.
  print 'router bgp %s' % (ASN)
  for vlan in allVlans:
    print '  vlan %s' % (vlan)
    print '    rd '+ROUTERID+':'+vlan
    print '    route-target import '+vlan+':'+vlan
    print '    route-target export '+vlan+':'+vlan
    print '    redistribute learned'
    print '    !'
  print '!'

if __name__ == "__main__":
    main()
