import jsonrpclib
import itertools
import netaddr
from cvplibrary import Form
from cvplibrary import CVPGlobalVariables, GlobalVariableNames
from cvplibrary import RestClient
import json
import re

#GET VARIABLES FROM CVP, USED TO AUTH TO DEVICE.
ip = CVPGlobalVariables.getValue(GlobalVariableNames.CVP_IP)
user = CVPGlobalVariables.getValue(GlobalVariableNames.CVP_USERNAME)
passwd = CVPGlobalVariables.getValue(GlobalVariableNames.CVP_PASSWORD)

"""
Instructions:
   - Create static configlet with VLANID and Description per line, separated by a comma:
      eg: 5,DynVLAN5
          10,DynVLAN10
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

def main():
  # Runs API call to grab configlet
  client = RestClient(restcall,'GET')
  if client.connect():
    # Parses configlet data into JSON.
    configletData = json.loads(client.getResponse())['config']
    # Splits configlet into list, divided at \n
    allVlans = configletData.split('\n')
    # Adds all lines to a list called allVlans
    vlanList.extend(allVlans)

  #SESSION SETUP FOR eAPI TO DEVICE
  url = "https://%s:%s@%s/command-api" % (user, passwd, ip)
  ss = jsonrpclib.Server(url)
  #CONNECT TO DEVICE
  response = ss.runCmds( 1, [ 'show ip bgp' ] ) # run command 'show ip bgp' and store output as response.
  ASN =  response[0]['vrfs']['default']['asn'] # grab ASN from BGP JSON data.
  ROUTERID = response[ 0 ]['vrfs']['default']['routerId'] # grab Router-ID from BGP JSON data.

  # !DynConfig is to Rename Configlet Automatically if needed;
  #        see: https://github.com/brokenpackets/configlet_AutoRename/ for details.
  print '!DynConfig '+hostname+'_AutoVLAN'
  allVlans = []
  #Create VLAN
  for vlan in vlanList:
    vlanId = vlanNumRegex.match(vlan).group(1)
    vlanName = vlanNameRegex.match(vlan).group(1)
    allVlans.append(vlanId)
    print 'vlan %s' % (vlanId)
    print ' name %s' % (vlanName)
    print '!'
    #Create VLAN Interface
    print 'interface Vlan %s' % (vlanId)
    print ' description %s' % (vlanName)
    print ' shutdown'
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
