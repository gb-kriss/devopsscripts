#!/usr/bin/env python
# -*- coding: utf-8 -*-
import optparse
import boto3
import time
import datetime
import optparse
import smtplib
from email.mime.text import MIMEText
from boto3 import ec2



def sendEmail(mailid,message,region):
        msg=MIMEText(message)
        msg['Subject'] = 'Reserved instances due for expiry in ' + region
        server = smtplib.SMTP('localhost:10025')
        server.sendmail("cron@ops.socialtwist.com", mailid, msg.as_string())
        server.quit()

parser = optparse.OptionParser(description="Shows summary about 'Reserved' and 'On-demand' ec2 instances")
parser.add_option("--aws-access-key", type=str, default=None, help="AWS Access Key ID. Defaults to the value of the AWS_ACCESS_KE    Y_ID environment variable (if set)")
parser.add_option("--aws-secret-key", type=str, default=None, help="AWS Secret Access Key. Defaults to the value of the AWS_SECRE    T_ACCESS_KEY environment variable (if set)")
parser.add_option("--region", type=str, default="us-east-1", help="AWS Region name. Default is 'us-east-1'")
parser.add_option("--email-id", type=str, default=None, help="Email address to send mail")
parser.add_option("-w", "--warn-time", type=int, default=2, help="Expire period for reserved instances in days. Default is '2 day    s'")
args, _ = parser.parse_args()


conn = boto3.client('ec2',region_name=args.region, aws_access_key_id=args.aws_access_key , aws_secret_access_key=args.aws_secret_key)
filters = [{ 'Name': 'instance-state-name', 'Values': ['running']}]
instances =  (conn.describe_instances(Filters = filters )) 


#Printing list of running instances
running_instances = {}
for instance in instances["Reservations"]:
    for ins in instance["Instances"]:
        running_instances[ins["InstanceType"]] = running_instances.get(ins["InstanceType"], 0 ) + 1


response = conn.describe_reserved_instances(
            Filters=[
                     {
                          'Name': 'scope',
                           'Values': [
                              'Region',
                                  ],
                            'Name': 'state',
                             'Values': [
                              'active',
                              ]
                                },
                            ],  
            )

print "reserved instances are ..."

#Printing list of reserved instances
reserved_instances = {}
soon_expire_ri = {}
for responses in response["ReservedInstances"]:
        reserved_instances[responses["InstanceType"]] = reserved_instances.get(responses["InstanceType"] , 0 ) + responses["InstanceCount"] 
        expire_time = time.mktime(datetime.datetime.strptime( str(responses["End"]), '%Y-%m-%d %H:%M:%S+00:00').timetuple())
        print expire_time
        if (expire_time - time.time()) < args.warn_time * 86400:
            soon_expire_ri[responses["ReservedInstancesId"]] = (responses["InstanceType"], responses["End"])

print soon_expire_ri                    
print "reserved instances List"
print reserved_instances

diff = dict([(x, reserved_instances[x] - running_instances.get(x, 0)) for x in reserved_instances])

for pkey in running_instances:
    if pkey not in reserved_instances:
        diff[pkey] = -running_instances[pkey]

unused_ri = dict((k, v) for k, v in diff.iteritems() if v > 0)
print "unused reserved instances"
print unused_ri
unreserved_instances = dict((k,-v) for k, v in diff.iteritems() if v < 0)
print "unreserved instances"
print unreserved_instances

print "unused reserved instances"
for k, v in unused_ri.iteritems():
    print("\t(%s)\t%s%s" %(v, k[0],k[1]))
if not unused_ri:
    print("\tNone")

body=""
for k, v in soon_expire_ri.iteritems():
    print(''.join((v[0])), datetime.datetime.strptime( str(v[1]), '%Y-%m-%d %H:%M:%S+00:00').strftime('%Y-%m-%d'))
    body += ("\t%s\t%s\n" %(str(v[0]), datetime.datetime.strptime( str(v[1]), '%Y-%m-%d %H:%M:%S+00:00').strftime('%Y-%m-%d')))
if body:
    emailid=args.email_id
    sendEmail(emailid,str(body), args.region)
if not soon_expire_ri:
    print("\tNone")
print("")

print("Running on-demand instances:   %s" % sum(running_instances.values()))
print("Reserved instances:            %s" % sum(reserved_instances.values()))
print("")
