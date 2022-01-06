import requests
import smtplib
from time import sleep

PREFIX = "https://localhost:35113/api/"


def send_email(email_address, contacts, subject, message, smtp_server, port):
    message = "Subject:" + subject + "\n\n" + message
    with smtplib.SMTP(host=smtp_server, port=port) as server:
        server.sendmail(email_address, contacts, message)


def verify_response(response):
    if str(response) == "<Response [200]>":
        response_json = response.json()

        if response_json["Success"]:
            return response_json
        else:
            print("Error from server:\n " + str(response_json['ErrorMessage']))
    else:
        print("Recived: " + str(response))
    return False


def track_long_operation(token, vm_ref, op_guid, connection_attemps=10, reconnect_timeout=30):
    sleep(5)
    res = get_op_status(token, op_guid)
    prev_percentage = -1
    #print("res of operation after start backup after sleep:", str(res))  # TODO: to delete
    while res['Statuses'] and res['Statuses'][0]['Status'] == 'Processing':
        cur_percentage = res['Statuses'][0]['Percentage']

        if not (prev_percentage == cur_percentage):
            print(end="\r")
            if cur_percentage == 100:
                print('Progress: ' + str(cur_percentage) + '%  |  ' + res['Statuses'][0]['SubOperation'] + "\t\t")
                print("operation proggress result: " + str(res))
            else:
                print('Progress: ' + str(cur_percentage) + '%  |  ' + res['Statuses'][0]['SubOperation'] + "\t\t", end="")
            prev_percentage = cur_percentage

        end_session(token)
        sleep(30*1)  # wait 1 minutes TODO: update sleep time
        token = start_session("Administrator", "radware10?", "ALTARO", 35107, "localhost")
        retries = 0

        while not token:
            if retries < connection_attemps:
                print("couldn't connect to Altaro server, retry connecting.... | " + str((retries + 1)) + "/" + str(
                    connection_attemps) + " attempts")
                sleep(reconnect_timeout)  # wait 1 minutes
                token = start_session("Administrator", "radware10?", "ALTARO", 35107, "localhost")
                retries += 1

        if not token:
            break

        res = get_op_status(token, op_guid)

    sleep(10)
    res = get_vm_report_status(token, vm_ref)
    #print("res: ", str(res))  # TODO: to delete
    if res['BackupReports'] and res['BackupReports'][0]['Result'] == 'Success':
        return True, token
    else:
        return False, token


# gets connections and credentials data, return session token
def start_session(user, password, domain, port, host):
    body = {
            "ServerPort": port,
            "ServerAddress": host,
            "Domain": domain,
            "Username": user,
            "Password": password
            }
    request = PREFIX + "sessions/start"
    response = requests.post(request, json=body, verify=False)
    response = verify_response(response)
    if response:
        return response["Data"]

    return False


# End session by token
def end_session(token):
    request = PREFIX + "sessions/end/" + token
    response = requests.post(request, verify=False)
    response = verify_response(response)
    if response:
        return True

    return False


# End all sessions
def end_all_sessions():
    request = PREFIX + "sessions/end"
    response = requests.post(request, verify=False)
    response = verify_response(response)
    if response:
        return True

    return False


# get all VM's that Altaro tracking
def get_all_vms(token, configured_only=0):
    request = PREFIX + "vms/list/" + token + "/" + str(configured_only)
    response = requests.get(request, verify=False)
    response = verify_response(response)

    if response:
        return response

    return False


# search for vm by vm name and return list of all matches vms
def get_vm_by_name(vm_name, token, configured_only=0):
    response = get_all_vms(token, configured_only=configured_only)

    if response:
        all_vms = response["VirtualMachines"]
        match_vms = []

        for vm in all_vms:
            if vm_name == vm['VirtualMachineName']:
                match_vms.append(vm)

        return match_vms

    return False


# performing rediscovering of new hosts and vms
def rediscover_vms(token):
    request = PREFIX + "vms/rediscover/" + token
    response = requests.post(request, verify=False)
    response = verify_response(response)

    if response:
        return True

    return False


# get status of all operations
def all_operations_status(token):
    request = PREFIX + "activity/operation-status/" + token
    response = requests.get(request, verify=False)
    response = verify_response(response)

    if response:
        return response["Statuses"]

    return False


# get list of backup and offsite locations by AltaroVirtualMachineRef
def get_vms_backuplocations(token, vm_ref, includeBackupLocations=0, includeOffsiteLocations=0):
    request = PREFIX + "vms/backuplocations/" + token + "/" + vm_ref + "/" + str(includeBackupLocations) + "/" + str(includeOffsiteLocations)
    response = requests.get(request, verify=False)
    response = verify_response(response)

    if response:
        return response["BackupLocations"]

    return False


# configure unconfigured vms and return newly created AltaroVirtualMachineRef
def configure_vm(token, hypervisorvirtualmachineuuid, altarohypervisorref):
    request = PREFIX + "vms/enable-configuration/" + token + "/" + hypervisorvirtualmachineuuid + "/" + altarohypervisorref
    response = requests.post(request, verify=False)
    response = verify_response(response)

    if response:
        return response["Data"]

    return False


# get all backup locations configured in ALTARO system
def get_backup_locations(token, includeBackupLocations=1, includeOffsiteLocations=1):
    request = PREFIX + "backuplocations/" + token + "/" + str(includeBackupLocations) + "/" + str(includeOffsiteLocations)
    response = requests.get(request, verify=False)
    response = verify_response(response)

    if response:
        return response["BackupLocations"]

    return False


# associate VM to backup location
def configure_vm_backup_location(token, altarovirtualmachineref, backuplocationid):
    request = PREFIX + "vms/backuplocations/" + token + "/" + altarovirtualmachineref + "/" + backuplocationid
    response = requests.post(request, verify=False)
    response = verify_response(response)

    if response:
        return True

    return False


def get_all_running_instructions(token):
    request = PREFIX + "activity/operation-status/" + token
    response = requests.get(request, verify=False)
    response = verify_response(response)

    if response:
        return response

    return False


# perform backup to VM
def take_backup(token, altarovirtualmachineref):
    request = PREFIX + "instructions/take-backup/" + token + "/" + str(altarovirtualmachineref)
    response = requests.post(request, verify=False)
    response = verify_response(response)

    if response:
        return response

    return False


# get status of operation by Guid
def get_op_status(token, op_guid):
    request = PREFIX + "activity/operation-status/" + token + "/" + str(op_guid)
    response = requests.get(request, verify=False)
    response = verify_response(response)

    if response:
        return response

    return False


# get status report on VM operation
def get_vm_report_status(token, altarovirtualmachineref):
    request = PREFIX + "reports/backup/" + token + "/" + str(altarovirtualmachineref)
    response = requests.get(request, verify=False)
    response = verify_response(response)

    if response:
        return response

    return False


# search for host by host name and return list of all matches hosts
def get_host_by_name(token, host_name):
    request = PREFIX + "restore-options/available-hosts/" + token
    response = requests.get(request, verify=False)
    response = verify_response(response)

    if response:
        all_hosts = response["Hosts"]
        match_hosts = []

        for host in all_hosts:
            if host_name == host['HostName']:
                match_hosts.append(host)

        return match_hosts

    return False


# get status report on VM operation
def get_available_datastores_by_host(token, altarohostref):
    request = PREFIX + "restore-options/available-datastores/" + token + "/" + altarohostref
    response = requests.get(request, verify=False)
    response = verify_response(response)

    if response:
        return response

    return False


# take offsite copy to VM
def take_offsite_copy(token, altarovirtualmachineref):
    request = PREFIX + "instructions/take-offsitecopy/" + token + "/" + str(altarovirtualmachineref)
    response = requests.post(request, verify=False)
    response = verify_response(response)

    if response:
        return response

    return False


# restore VM from backup location
def restore_vm(token, HypervisorVirtualMachineUuid, RestoreFromLocationId, RestoreBackupVersion, OriginalVirtualMachineName, RestoredVirtualMachineName, DisableNicOnRestoredVirtualMachine, RestoreToAltaroHostId, RestoreToLocation, DecryptionKey, BackupFolderPath, CustomerId, BackupVerisonFormat, RestoreBackupVersionIsUtc):
    request = PREFIX + "instructions/take-offsitecopy/" + token + "/" + str(altarovirtualmachineref)
    response = requests.post(request, verify=False)
    response = verify_response(response)

    if response:
        return response

    return False


#  get_available backup versions of VM
def get_available_versions(token, vm_ref, backup_location_id):
    request = PREFIX + "restore-options/available-versions/" + token + "/" + vm_ref + "/" + backup_location_id
    response = requests.get(request, verify=False)
    response = verify_response(response)

    if response:
        return response

    return False


