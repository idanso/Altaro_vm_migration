from macros import *
from time import sleep
import urllib3
import sys

# for ignoring connection warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

vm_name = "vm_name"
email_to_notify = "test@email.com"

status_message = "Script ended with unexpected failure"

if len(sys.argv) > 1:
    vm_name = sys.argv[1]
    email_to_notify = sys.argv[2]
    user_name = sys.argv[3]
    password = sys.argv[4]

try:
    print("Connecting to Altaro...")
    token = start_session(user_name, password, "ALTARO", 35107, "localhost")
    if token:
        print("Session Started")

        print("Searching VM...")
        match_vms = get_vm_by_name(vm_name, token)
        print("List of found VM's:")  # Consider Deleting
        #print(match_vms)

        if len(match_vms) < 1:
            print("VM not found, rediscover new VM's... ")
            result = rediscover_vms(token)

            if result:
                print("Rediscover finished")
                print("Searching VM...")
                match_vms = get_vm_by_name(vm_name, token)
                print("List of found VM's:")  # Consider Deleting
                print(match_vms)

        if len(match_vms) > 0:
            print("VM Found")
            print("Checking if VM configured...")

            if match_vms[0]['Configured']:
                vm_ref = match_vms[0]['AltaroVirtualMachineRef']

            else:
                print("VM Not configure, starting VM Configuration...")
                vm_ref = configure_vm(token, match_vms[0]['HypervisorVirtualMachineUuid'], match_vms[0]['AltaroHypervisorRef'])
                sleep(5)

            if vm_ref:
                print("VM configured")
                print("Configuring local backup location...")

                backup_location = get_backup_locations(token, includeBackupLocations=1, includeOffsiteLocations=0)
                local_location_ref = backup_location[0]["BackupLocationId"]
                res = configure_vm_backup_location(token, vm_ref, local_location_ref)
                sleep(5)

                if res:
                    print("Local backup configured successfully")
                    print("Configuring offsite backup location...")
                    backup_location = get_backup_locations(token, includeBackupLocations=0, includeOffsiteLocations=1)
                    offsite_location_ref = backup_location[0]["BackupLocationId"]
                    res = configure_vm_backup_location(token, vm_ref, offsite_location_ref)
                    sleep(5)

                    if res:
                        print("Offsite backup configured successfully")
                        print("Verifing VM backup location...")
                        vm_backup_locations = get_vms_backuplocations(token, vm_ref,
                                                                     includeBackupLocations=1,
                                                                     includeOffsiteLocations=1)
                        #print(vm_backup_locations)

                        if vm_backup_locations and len(vm_backup_locations) == 2:  # TODO: consider to verify by location reference
                            print("All backup locations configures successfully")
                            print("Starting VM backup operation...")
                            res = take_backup(token, vm_ref)

                            if res:
                                print("Backup started successfully (May take a few hours depends on VM disk size)...")
                                #print(res)
                                backup_op_guid = res['Data']
                                sleep(5)
                                res, token = track_long_operation(token, vm_ref, backup_op_guid, connection_attemps=10)

                                if res:
                                    print("Backup  finished successfully")
                                    print("Taking offsite copy...")
                                    sleep(5)
                                    res = take_offsite_copy(token, vm_ref)

                                    if res['Result']:
                                        print("Taking offsite copy started successfully (May take a few hours depends on VM disk size)...")
                                        #print(res)
                                        backup_op_guid = res['Data']
                                        sleep(5)
                                        res, token = track_long_operation(token, vm_ref, backup_op_guid, connection_attemps=10, reconnect_timeout=30)
                                        if res:
                                            status_message = "Taking offsite copy finished successfully and ready for restore on the other site"

                                        else:
                                            status_message = "Taking offsite copy operation encountered an error :("
                                    else:
                                        status_message = "Failed starting offsite copy :("
                                else:
                                    status_message = "Backup operation encountered an error :("
                            else:
                                status_message = "Failed starting backup :("
                    else:
                        status_message = "Configuring offsite backup failed :("
                else:
                    status_message = "Configuring local backup failed :("
            else:
                status_message = "VM configuration failed :("
        else:
            status_message = "VM not found, ensure vm is one of ESXI's 1-8 if not migrate it :("
    else:
        status_message = "Error in getting token :("

finally:
    if token:
        print(status_message)
        #macros.end_session(token)
        end_all_sessions()
        print('Session closed')
        print("Sending status email...")
        message = "Virtual machine: " + vm_name + "\nStatus: " + status_message
        send_email("altaro.backup@radwaretraininglab.com", [email_to_notify],
                   "Altaro Backup Proccess finished", message, "10.250.0.26", 25)
        print("Email sent")

print('Script ended')
