# 2019 Team 13

from kubernetes import client, config
# install pick using "pip install pick". It is not included
# as a dependency because it only used in examples
from pick import pick
import subprocess
import time

def main():
    timestr = time.strftime("%Y%m%d-%H%M%S")
    contexts, active_context = config.list_kube_config_contexts()
    if not contexts:
        print("Cannot find any context in kube-config file.")
        return
    # Python List of all contexts for use by PICK Module
    contexts = [context['name'] for context in contexts]

    active_index = contexts.index(active_context['name'])
    cluster1, first_index = pick(contexts, title="Pick the source Cluster Context for the POD to be backed up",
                                 default_index=active_index)

    client1 = client.CoreV1Api(
        api_client=config.new_client_from_config(context=cluster1))

    cluster2, _ = pick(contexts, title="Pick the target Cluster Context for the POD to be restored to",
                       default_index=first_index)

    client2 = client.CoreV1Api(
        api_client=config.new_client_from_config(context=cluster2))

    # Create Python List of all PODs in SRC Namespace for PICK Module
    source_pods = [i.metadata.name for i in client1.list_pod_for_all_namespaces().items]
    # DEBUGONLY print("\nList of source_pods on %s:" % source_pods)
    selected_pod = pick(source_pods, title="Pick the POD to be backed up")

    for i in client1.list_pod_for_all_namespaces().items:
        if selected_pod[0] == i.metadata.name: # Return the Kubernetes API POD object
            print("Found the POD Object for Selected POD")
            source_pod_object = i

    print ('This is the POD you selected {0}'.format(source_pod_object.metadata.name))

    # Grabbing labels from the POD object we now have.
    #print("Labels for our POD to be backed up" )
    #print("%s" % (source_pod_object.metadata.labels))

    # Create a LIST from the Labels Dict
    labels_list = [[k, v] for k, v in source_pod_object.metadata.labels.items()]
    #print(labels_list[0])
    #print(type(labels_list))

    # Will need to work on this in future - Currently takes first label for the pod
    # usually app=xyz so this works. Can easily make a label selector for user to choose.
    selector = '{0}={1}'.format(labels_list[0][0],labels_list[0][1])
    backup_name = '{0}-{1}-{2}'.format(labels_list[0][0], labels_list[0][1],timestr)
    print("selector string is", selector)

    ## VELERO WORK

    # VELERO BACKUP Section
    backup_create_cmd = ['velero', 'backup', 'create', backup_name, '--selector', selector, '-w', '--kubecontext', cluster1]
    subprocess.check_call(backup_create_cmd)

    # VELERO BACKUP Status
    backup_query_cmd = ['velero', 'backup', 'describe', backup_name, '--kubecontext',cluster1]
    subprocess.check_call(backup_query_cmd)

    # TEMP for testing purposes delete the namespace before restoring to same location
    k8s_delete_ns_cmd = ['kubectl', 'delete', 'namespace', 'lucky13','--force']
    subprocess.check_call(k8s_delete_ns_cmd)

    # VELERO Restore
    restore_create_cmd = ['velero', 'restore', 'create', backup_name, '--from-backup', backup_name, '-w','--kubecontext',cluster2]
    subprocess.check_call(restore_create_cmd)

    # VELERO Restore Describe
    restore_describe_cmd = ['velero', 'restore', 'describe', backup_name, '--kubecontext',cluster2]
    subprocess.check_call(restore_describe_cmd)

    # VELERO BACKUP Delete
    backup_delete_cmd = ['velero', 'backup', 'delete', backup_name, '--kubecontext',cluster2]
    subprocess.check_call(backup_delete_cmd)

    '''
    Velero Pseudo Code Placeholder
    Velero create backup
    velero backup create nginx-backup --selector app=nginx
    return backup name
    velero get backup <name>
    Wait until we get a response. This will error out until the DST K8s cluster synchronizes with the backup
    metadata on the S3 Datastore. When it starts responding we can move onto Restore.
    
    Check for Destinatinon Health Check is GOOD
    Once Health Check is good - (Liveness Probes, Health Proves) then Proceed
    Delete the POD(s) in the Source Cluster.
    
    
    '''




    print('KMotioning POD {0} from {1} cluster to {2} cluster... '.format(source_pod_object.metadata.name, cluster1, cluster2))


    '''
    print("\n\nList of pods on %s:" % cluster2)
    for i in client2.list_pod_for_all_namespaces().items:
        print("%s\t%s\t%s" %
              (i.status.pod_ip, i.metadata.namespace, i.metadata.name))
    '''

if __name__ == '__main__':
    main()