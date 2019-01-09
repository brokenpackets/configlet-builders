import jsonrpclib
from cvplibrary import CVPGlobalVariables, GlobalVariableNames
from cvplibrary import RestClient
import json
import ssl
from netaddr import *

# Ignore untrusted certificate for eAPI call.
ssl._create_default_https_context = ssl._create_unverified_context

#GET VARIABLES FROM CVP, USED TO AUTH TO DEVICE.
ip = CVPGlobalVariables.getValue(GlobalVariableNames.CVP_IP)
user = CVPGlobalVariables.getValue(GlobalVariableNames.CVP_USERNAME)
passwd = CVPGlobalVariables.getValue(GlobalVariableNames.CVP_PASSWORD)

"""
Instructions:
   - Create static configlet with switch hostname, vlan id, vlan name,
     switch-specific ip address, and vrf.
   - For unrouted VLAN, enter switch hostname, vlan id, vlan name, and 'unrouted' 
      eg: DC1-Compute1,100,Compute1,10.10.10.1/24,production
          DC1-Compute1,200,iSCSI1,unrouted
   - Rename user variable 'configlet' to match configlet name.
   - Apply configlet to container - if any new VLANs are added, remove configlet
     and re-add.
"""

### User variables
configlet = 'TMPLT_Compute_Specific_VLANs'

### Rest of script
cvpserver = 'localhost'
restcall = 'https://'+cvpserver+':443//cvpservice/configlet/getConfigletByName.do?name='+configlet

def main():
  # Runs API call to grab configlet
  client = RestClient(restcall,'GET')
  if client.connect():
    # Parses configlet data into JSON.
    configletData = json.loads(client.getResponse())['config']
    # Splits configlet into list, divided at \n
    vlanList = list(configletData.split('\n'))

  #SESSION SETUP FOR eAPI TO DEVICE
  url = "https://%s:%s@%s/command-api" % (user, passwd, ip)
  ss = jsonrpclib.Server(url)
  #CONNECT TO DEVICE
  response = ss.runCmds(1,['show ip bgp']) # run command 'show ip bgp' and store output as response.
  ASN =  response[0]['vrfs']['default']['asn'] # grab ASN from BGP JSON data.
  ROUTERID = response[0]['vrfs']['default']['routerId'] # grab Router-ID from BGP JSON data.
  HOSTNAME = ss.runCmds(1,['show hostname'])[0]['hostname']
  
  l2Vlans = []
  l3Vlans = []
  allVrfs = {}
  #Create VLAN
  for vlan in vlanList:
    vlanInfo = vlan.split(',')
    hostname = vlanInfo[0]
    if hostname == HOSTNAME:
      vlanID = vlanInfo[1]
      vlanName = vlanInfo[2]
      vlanIP = vlanInfo[3]
      if vlanIP == 'unrouted':
        l2Vlans.append(vlanID)
      else:
        gatewayIP = (IPNetwork(vlanIP).first+1)
        l3Vlans.append(vlanID)
        vrfName = vlanInfo[4]
        if vrfName in allVrfs.keys():
          allVrfs[vrfName].append(vlanIP)
        else:
          allVrfs.update({vrfName:[vlanIP]})
      print 'vlan %s' % (vlanID)
      print '  name %s' % (vlanName)
      print '!'
      #Create VLAN Interface
      if vlanID in l3Vlans:
        print 'interface Vlan %s' % (vlanID)
        print '  description %s' % (vlanName)
        print '  vrf forwarding %s' % (vrfName)
        print '  ip address %s' % (vlanIP)
        print '  ip virtual-router address %s' % (str(IPAddress(gatewayIP)))
        print '!'
  #Create MACVRF for EVPN.
  print 'router bgp %s' % (ASN)
  for vrf in allVrfs:
    print '  vrf %s' % (vrf)
    for netblock in allVrfs[vrf]:
      print '    network '+str(IPNetwork(netblock).cidr)
  print '!'

if __name__ == "__main__":
    main()
