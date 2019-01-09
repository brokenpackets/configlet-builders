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
   - Create static configlet with VLANID, Description, anycast gateway IP,
     and vrf name (optional) per line, separated by a comma:
      eg: 5,DynVLAN5,192.168.5.1/24,production
          10,DynVLAN10,192.168.10.1/24,development
          20,DynVLAN20,192.168.20.1/24
   - Rename user variable 'configlet' to match configlet name.
   - Apply configlet to container - if any new VLANs are added, remove configlet and re-add.
"""

### User variables
configlet = 'TMPLT_Compute_VLANs'

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
  allVlans = []
  allVrfs = {}
  #Create VLAN
  for vlan in vlanList:
    vlanInfo = vlan.split(',')
    vlanId = vlanInfo[0]
    vlanName = vlanInfo[1]
    ipAddr = vlanInfo[2]
    if len(vlanInfo) == 4:
      vrfName = vlanInfo[3]
    allVlans.append(vlanId)
    if vrfName:
      if vrfName in allVrfs.keys():
        allVrfs[vrfName].append(ipAddr)
      else:
        allVrfs.update({vrfName:[ipAddr]})
    print 'vlan %s' % (vlanId)
    print ' name %s' % (vlanName)
    print '!'
    #Create VLAN Interface
    print 'interface Vlan %s' % (vlanId)
    print ' description %s' % (vlanName)
    if vrfName:
      print ' vrf forwarding %s' % (vrfName)
    print ' ip address virtual %s' % (ipAddr)
    print '!'
    vrfName = ''
    
  #Assign VLAN to VNI
  print 'interface vxlan1'
  for vlan in allVlans:
    print '  vxlan vlan '+vlan+' vni '+str(int(vlan)+10000)
  print '!'
  #Create MACVRF for EVPN.
  print 'router bgp %s' % (ASN)
  for vlan in allVlans:
    print '  vlan %s' % (vlan)
    print '    rd '+ROUTERID+':'+str(int(vlan)+10000)
    print '    route-target import '+str(int(vlan)+10000)+':'+str(int(vlan)+10000)
    print '    route-target export '+str(int(vlan)+10000)+':'+str(int(vlan)+10000)
    print '    redistribute learned'
    print '    !'
  if allVrfs:
    for vrf in allVrfs.keys():
      print '  vrf '+vrf
      for netblock in allVrfs[vrf]:
        print '    network '+str(IPNetwork(netblock).cidr)
  print '!'
if __name__ == "__main__":
    main()
