import jsonrpclib
from cvplibrary import CVPGlobalVariables, GlobalVariableNames, RestClient, Device
import json
import re
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
   - Create static configlet with VNI, VRFName per line, separated by a comma:
      eg: 21100,Development
          21200,Staging
   - Rename user variable 'vrf_configlet' to match vrf configlet name.
   - Apply configlet to container - if any new VRFs are added, 
     remove configlet and re-add.
   - Create static configlet with VLANID, Description, anycast gateway IP,
     and vrf name (optional) per line, separated by a comma:
      eg: 5,DynVLAN5,192.168.5.1/24,production
          10,DynVLAN10,192.168.10.1/24,development
          20,DynVLAN20,192.168.20.1/24
   - Rename user variable 'l3evpn_configlet' to match configlet name.
   - Apply configlet to container - if any new VLANs are added, remove configlet and re-add.
"""

### User variables
vrf_configlet = 'TMPLT_VRF_VNI'
l3evpn_configlet = 'TMPLT_Compute_VLANs'

### Rest of script
cvpserver = 'localhost'
restcall = 'https://'+cvpserver+':443/cvpservice/configlet/getConfigletByName.do?name='

def main():
  # Runs API call to grab configlet
  client = RestClient(restcall+vrf_configlet,'GET')
  if client.connect():
    # Parses configlet data into JSON.
    configletData = json.loads(client.getResponse())['config']
    # Splits configlet into list, divided at \n
    vrfList = configletData.split('\n')
    vrfList.pop(0)
  client = RestClient(restcall+l3evpn_configlet,'GET')
  if client.connect():
    # Parses configlet data into JSON.
    configletData = json.loads(client.getResponse())['config']
    # Splits configlet into list, divided at \n
    vlanList = configletData.split('\n')
    vlanList.pop(0)
  #SESSION SETUP FOR eAPI TO DEVICE 
  # Deprecating jsonrpc, moving to Device() library.
  ##url = "https://%s:%s@%s/command-api" % (user, passwd, ip)
  ##ss = jsonrpclib.Server(url)
  device = Device(ip)
  
  #CONNECT TO DEVICE
  response = device.runCmds(['show ip bgp']) # run command 'show ip bgp' and store output as response
  ASN =  response[0]['response']['vrfs']['default']['asn'] # grab ASN from BGP JSON data.
  ROUTERID = response[0]['response']['vrfs']['default']['routerId'] # grab Router-ID from BGP JSON data.

  ####### VRF Config
  #Create VRF
  allVlans = []
  allVrfs = {}
  allVrfs_evpn = {}
  for vrf in vrfList:
    vrfInfo = vrf.split(',')
    vrfId = vrfInfo[0]
    vrfVNI = vrfInfo[1]
    allVrfs.update({vrfId:vrfVNI})
    print 'vrf definition %s' % (vrfId)
    print '!'
    print 'ip routing vrf %s' % (vrfId)
    print '!'
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
      if vrfName in allVrfs_evpn.keys():
        allVrfs_evpn[vrfName].append(ipAddr)
      else:
        allVrfs_evpn.update({vrfName:[ipAddr]})
    print 'vlan %s' % (vlanId)
    print '   name %s' % (vlanName)
    print '!'
    #Create VLAN Interface
    print 'interface Vlan %s' % (vlanId)
    print '   description %s' % (vlanName)
    if vrfName:
      print '   vrf forwarding %s' % (vrfName)
    print '   ip address virtual %s' % (ipAddr)
    print '!'
    vrfName = ''
  #Assign VLAN to VNI
  print 'interface vxlan1'
  for vrfname in allVrfs:
    print '   vxlan vrf '+vrfname+' vni '+allVrfs[vrfname]
  for vlan in allVlans:
    print '   vxlan vlan '+vlan+' vni '+str(int(vlan)+10000)
  print '!'

  #Create VRF for EVPN.
  print 'router bgp %s' % (ASN)
  for vrf in allVrfs.keys():
    print '  vrf %s' % (vrf)
    print '    rd '+ROUTERID+':'+allVrfs[vrf]
    print '    route-target import '+allVrfs[vrf]+':'+allVrfs[vrf]
    print '    route-target export '+allVrfs[vrf]+':'+allVrfs[vrf]
    for netblock in allVrfs_evpn[vrf]:
        print '    network '+str(IPNetwork(netblock).cidr)
    print '    !'
  for vlan in allVlans:
    print '  vlan %s' % (vlan)
    print '    rd '+ROUTERID+':'+str(int(vlan)+10000)
    print '    route-target import '+str(int(vlan)+10000)+':'+str(int(vlan)+10000)
    print '    route-target export '+str(int(vlan)+10000)+':'+str(int(vlan)+10000)
    print '    redistribute learned'
    print '    !'
  print '!'
  
if __name__ == "__main__":
    main()
