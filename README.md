# kMigrate
kmigrate is a wrapper script that uses the kubernetes python client and velero under the covers to very quickly migrate an entire kubernetes application (including Services, Deployments, PODs) from one Kubernetes cluster to another.

## Prerequisites
To leverage kMigrate you will need the following.
1. Python3 Installed with Kubernetes Client and pick Modules installed.
3. Velero CLI installed and Velero installed in both SRC and DST Kubernetes clusters. https://heptio.github.io/velero/master/install-overview
4. Velero configured to use a shared S3 bucket as indicated https://heptio.github.io/velero/master/migration-case.html
5. kubectl and a local kubeconfig file with two clusters configured and access to those two clusters on the same machine you will run kMigrate on.

## Install required Python3 Modules
    $ pip install kubernetes
    $ pip install pick

## Prepare S3 Bucket (Can also use Minio)
    Use Amazon S3 Console to create a storage bucket
    Validate you can access storage bucket from your Linux machine
    $ aws configure
    $ aws s3 ls
        2019-12-05 08:40:40 cf-templates-cppvrc58u29n-us-east-1
        2020-05-31 03:55:46 com.vmware.cso.cm.659204632508-tf
        2022-06-07 22:55:13 tk-velero
    
## Install Velero CLI
    $ wget https://github.com/vmware-tanzu/velero/releases/download/v1.8.1/velero-v1.8.1-linux-amd64.tar.gz
    $ tar -xvzf velero-v1.8.1-linux-amd64.tar.gz
    $ sudo cp velero-v1.8.1-linux-amd64/velero /usr/local/bin
    $ velero version

## Install Velero to both clusters with S3 as Storage Provider
    Create velero S3 Credentials file
    $ vi aws-creds-velero
        [default]
        AWS_ACCESS_KEY_ID=AS....NKUQ
        AWS_SECRET_ACCESS_KEY=39....Ah
    $ kubectl config get-contexts
    INSTALL Velero to the SRC cluster (prod-small)
    $ kubectl config use-context prod-small
    $ velero install --provider aws --bucket tk-velero --secret-file ~/aws-creds-velero --backup-location-config region=us-east-1,s3ForcePathStyle="true",s3Url=http://tk-velero.s3.us-east-1.amazonaws.com --use-volume-snapshots=false --use-restic
    $ kubectl config use-context prod-med
    INSTALL Velero to the SRC cluster (prod-med)
    $ velero install --provider aws --bucket lucky13 --secret-file ~/velero-creds --backup-location-config region=minio,s3ForcePathStyle="true",s3Url=http://10.197.96.13:9000 --use-volume-snapshots=false --use-restic

## Install Velero to both clusters with Minio as Storage Provider
    Create velero S3 Credentials file
    $ vi minio-creds-velero
        [default]
        AWS_ACCESS_KEY_ID=AS....NKUQ
        AWS_SECRET_ACCESS_KEY=39....Ah
    $ kubectl config get-contexts
    INSTALL Velero to the SRC cluster (prod-small)
    $ kubectl config use-context prod-small
    $ velero install --provider aws --bucket tk-velero --secret-file ~/aws-creds-velero --backup-location-config region=us-east-1,s3ForcePathStyle="true",s3Url=http://10.197.96.13:9000 --use-volume-snapshots=false --use-restic
    $ kubectl config use-context prod-med
    INSTALL Velero to the SRC cluster (prod-med)
    $ velero install --provider aws --bucket lucky13 --secret-file ~/velero-creds --backup-location-config region=minio,s3ForcePathStyle="true",s3Url=http://10.197.96.13:9000 --use-volume-snapshots=false --use-restic
## Deploy a test Application with Service to migrate to a new cluster.

To deploy the sample workload into the Source Cluster:

    $ cd kmigrate
    $ kubectl config use-context prod-small
    $ kubectl apply -f sample/lucky13.yaml

This will create a namespace and add a deployment and service.

To view the page locally with a port forward:

    $ kubectl port-forward -n lucky13 svc/nginx 8000:80

Now navigate to http://localhost:8000/index.html in your browser.  The index page will show the name of the node on which the pod you're connected to is running.

NOTE:  To deploy a lucky13 web application on a Kubernetes cluster that is integrated with an external Load Balancer like F5, NSX-T, AWS, GCP etc) you can use the lucky13-lb-svc.yaml file instead.

    $ kubectl apply -f sample/lucky13-lb-svc.yaml
    
Verify application was deployed successfully.
    
    $ kubectl get all -n lucky13
    
You should two PODs, a service of type LB (If you used the lucky13-lb-svc.yaml) and a Deployment in the lucky13 Namespace.


## Use kMigrate to migrate the Lucky13 Application.

Run the kMigrate.py script

    $ ./kmigrate.py
    
1. Select the Source Cluster to find your PODs to backup and Hit Enter.
2. Select one of the lucky13 PODs in the Source Cluster and Hit Enter.
3. Select a Target Cluster to Migrate the application to.

kMigrate time will vary and most of the time will be waiting for the Target cluster to sync its know backups with the S3 backup to recognize the available backup is there to restore. This is not configurable and happens automatically every 60 seconds.


## Verify the Restored application is running successfully in the new cluster.

    $ kubectl config use-context prod-med
    $ kubectl get all -n lucky13
        NOTE: Verify the PODs, Deployment, and Service exists and is Running in the Target Cluster.
        
        Test the Application by accessing the EXTERNAL-IP for the Test Application listenting on Port 80.
        
    $ kubectl get svc -n lucky13
    $  curl $(k get svc -n lucky13 lucky13 -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
        <html>
        <body>
        <h1>Lucky 13!</h1>
        <p>My node name: 4743006a-12a8-482f-a096-71f01e423674</p>
        </body>
        </html>


## Lucky 13 Docker Image

This docker image uses the `index.sh` to generate an index page that displays the node on which the pod is running.  In order to alter this index page, simply alter the html that `index.sh` stamps out.  If you use additional environment variables, be sure to make the env vars available through the `sample/lucky13.yaml` manifest.  The existing example uses the downward API to set the `MY_NODE_NAME` var.

If you make a change to the index script, build a new image with:

    $ docker build -t myrepo/lucky13 .

And push the image:

    $ docker push myrepo/lucky13

Now replace the `lander2k2/lucky13` image name in `image/lucky13.yaml` with your new image and apply it:

    $ kubectl apply -f sample/lucky13.yaml

