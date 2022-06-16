from cvplibrary import CVPGlobalVariables, GlobalVariableNames, RestClient, Device
import json
import re
import ssl

# Ignore untrusted certificate for eAPI call.
ssl._create_default_https_context = ssl._create_unverified_context

#GET VARIABLES FROM CVP, USED TO AUTH TO DEVICE.
ip = CVPGlobalVariables.getValue(GlobalVariableNames.CVP_IP)
user = CVPGlobalVariables.getValue(GlobalVariableNames.CVP_USERNAME)
passwd = CVPGlobalVariables.getValue(GlobalVariableNames.CVP_PASSWORD)

### Rest of script
vlanList = []
intf_regex = re.compile('interface Ethernet.*')
intf_profile_regex = re.compile('profile (.*)')
profile_regex = re.compile('interface profile (.*)')
intf_comment_regex = re.compile('Dyn_intf = (.*)')
allConfiglets = {}

def main():
  #SESSION SETUP FOR eAPI TO DEVICE
  device = Device(ip)
  #CONNECT TO DEVICE
  runningconfig = device.runCmds(['show running-config'])[0]['response']['cmds']
  interfaceProfiles = []
  skipInterfaces = []
  profileList = [x for x in runningconfig.keys() if profile_regex.match(x)]
  for profile in profileList:
     interfaceProfiles.append({profile.replace('interface profile ',''):runningconfig[profile]['cmds'].keys()})
  keylist = [x for x in runningconfig.keys() if intf_regex.match(x)]
  for item in keylist:
    # Loop over item comments
    for line in runningconfig[item]['cmds']:
      # match interface profile
      if intf_profile_regex.match(line):
        profileName = intf_profile_regex.match(line).group(1)
        for profile in interfaceProfiles:
          if profile.keys()[0] == profileName:
              print item
              for command in profile[profileName]:
                print command.strip('command')
              print ' !! Dyn_intf = '+profileName
              skipInterfaces.append(item)
      # match comment against intf_comment_regex
    if item in skipInterfaces:
      pass
    else:
      for comment in runningconfig[item]['comments']:
        if intf_comment_regex.match(comment):
          profileName = intf_comment_regex.match(comment).group(1)
          for profile in interfaceProfiles:
            if profile.keys()[0] == profileName:
                print item
                for command in profile[profileName]:
                  print command.strip('command')
                print ' !! Dyn_intf = '+profileName

if __name__ == "__main__":
    main()
