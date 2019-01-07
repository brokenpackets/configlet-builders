import jsonrpclib
from cvplibrary import CVPGlobalVariables, GlobalVariableNames
from cvplibrary import RestClient
import json
import ssl
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
   - Rename user variable 'configlet' to match configlet name.
   - Apply configlet to container - if any new VRFs are added, 
     remove configlet and re-add.
"""

### User variables
configlet = 'TMPLT_VRF_VNI'

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
    vrfList = configletData.split('\n')
   
  #SESSION SETUP FOR eAPI TO DEVICE
  url = "https://%s:%s@%s/command-api" % (user, passwd, ip)
  ss = jsonrpclib.Server(url)
  #CONNECT TO DEVICE
  response = ss.runCmds(1,['show ip bgp']) # run command 'show ip bgp' and store output as response
  ASN =  response[0]['vrfs']['default']['asn'] # grab ASN from BGP JSON data.
  ROUTERID = response[0]['vrfs']['default']['routerId'] # grab Router-ID from BGP JSON data.

  #Create VRF
  allVrfs = {}
  for vrf in vrfList:
    vrfInfo = vrf.split(',')
    vrfVNI = vrfInfo[0]
    vrfId = vrfInfo[1]
    allVrfs.update({vrfId:vrfVNI})
    print 'vrf definition %s' % (vrfId)
    print '!'
    print 'ip routing vrf %s' % (vrfId)
    print '!'
  print 'interface vxlan1'
  for vrfname in allVrfs:
    print '   vxlan vrf '+vrfname+' vni '+str(int(allVrfs[vrfname])+20000)
  print '!'
  #Create VRF for EVPN.
  print 'router bgp %s' % (ASN)
  for vrf in allVrfs:
    print '  vrf %s' % (allVrfs[vrf])
    print '    rd '+ROUTERID+':'+allVrfs[vrf]
    print '    route-target import '+str(int(allVrfs[vrf])+20000)+':'+str(int(allVrfs[vrf])+20000)
    print '    route-target export '+str(int(allVrfs[vrf])+20000)+':'+str(int(allVrfs[vrf])+20000)
    print '    !'

if __name__ == "__main__":
    main()
