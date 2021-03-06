# Copyright 2020 The Kubernetes Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import zlib

template = """
- name: e2e-kops-grid{{suffix}}
  cron: '{{cron}}'
  labels:
    preset-service-account: "true"
    preset-aws-ssh: "true"
    preset-aws-credential: "true"
  decorate: true
  decoration_config:
    timeout: 90m
  spec:
    containers:
    - command:
      - runner.sh
      - /workspace/scenarios/kubernetes_e2e.py
      args:
      - --cluster=e2e-kops{{suffix}}.test-cncf-aws.k8s.io
      - --deployment=kops
      - --env=KUBE_SSH_USER={{kops_ssh_user}}
      - --env=KOPS_DEPLOY_LATEST_URL=https://storage.googleapis.com/kubernetes-release/release/stable.txt
      - --env=KOPS_KUBE_RELEASE_URL=https://storage.googleapis.com/kubernetes-release/release
      - --env=KOPS_RUN_TOO_NEW_VERSION=1
      - --extract=release/stable
      - --ginkgo-parallel
      - --kops-args={{kops_args}}
      - --kops-image={{kops_image}}
      - --kops-priority-path=/workspace/kubernetes/platforms/linux/amd64
      - --kops-ssh-user={{kops_ssh_user}}
      - --kops-version=https://storage.googleapis.com/kops-ci/bin/latest-ci-updown-green.txt
      - --provider=aws
      - --test_args={{test_args}}
      - --timeout=60m
      image: gcr.io/k8s-testimages/kubekins-e2e:v20200420-e830a3a-master
  annotations:
    testgrid-dashboards: google-aws, sig-cluster-lifecycle-kops
    testgrid-tab-name: {{tab}}
"""

# We support rapid focus on a few tests of high concern
# This should be used for temporary tests we are evaluating,
# and ideally linked to a bug, and removed once the bug is fixed
hotlist = [
    # flannel networking issues: https://github.com/kubernetes/kops/pull/8381#issuecomment-616689498
    'kops-grid-aws-flannel-centos7',
    'kops-grid-aws-flannel-rhel7',
    'kops-grid-aws-flannel-rhel8',
]

def simple_hash(s):
    return zlib.crc32(s.encode())

def build_cron(key, on_hotlist):
    minute = simple_hash("minutes:" + key) % 60
    hour = simple_hash("hours:" + key) % 24

    # hotlist tests run hourly
    if on_hotlist:
        return "%d * * * *" % (minute)

    # we normally run once per day
    return "%d %d * * *" % (minute, hour)

def build_test(cloud='aws', distro=None, networking=None):
    # pylint: disable=too-many-statements,too-many-branches

    if distro == 'amazonlinux2':
        kops_ssh_user = 'ec2-user'
        kops_image = '137112412989/amzn2-ami-hvm-2.0.20200304.0-x86_64-gp2'
    elif distro == 'centos7':
        kops_ssh_user = 'centos'
        kops_image = "679593333241/CentOS Linux 7 x86_64 HVM EBS ENA 1901_01-b7ee8a69-ee97-4a49-9e68-afaee216db2e-ami-05713873c6794f575.4" # pylint: disable=line-too-long
    elif distro == 'coreos':
        kops_ssh_user = 'core'
        kops_image = '595879546273/CoreOS-stable-2303.3.0-hvm'
    elif distro == 'debian9':
        kops_ssh_user = 'admin'
        kops_image = '379101102735/debian-stretch-hvm-x86_64-gp2-2019-11-13-63558'
    elif distro == 'debian10':
        kops_ssh_user = 'admin'
        kops_image = '136693071363/debian-10-amd64-20200210-166'
    elif distro == 'flatcar':
        kops_ssh_user = 'core'
        kops_image = '075585003325/Flatcar-stable-2303.3.1-hvm'
    elif distro == 'ubuntu1604':
        kops_ssh_user = 'ubuntu'
        kops_image = '099720109477/ubuntu/images/hvm-ssd/ubuntu-xenial-16.04-amd64-server-20191114'
    elif distro == 'ubuntu1804':
        kops_ssh_user = 'ubuntu'
        kops_image = '099720109477/ubuntu/images/hvm-ssd/ubuntu-bionic-18.04-amd64-server-20200323'
    elif distro == 'ubuntu2004':
        kops_ssh_user = 'ubuntu'
        kops_image = '099720109477/ubuntu/images-testing/hvm-ssd/ubuntu-focal-daily-amd64-server-20200414.1' # pylint: disable=line-too-long
    elif distro == 'rhel7':
        kops_ssh_user = 'ec2-user'
        kops_image = '309956199498/RHEL-7.7_HVM-20191119-x86_64-2-Hourly2-GP2'
    elif distro == 'rhel8':
        kops_ssh_user = 'ec2-user'
        kops_image = '309956199498/RHEL-8.1.0_HVM-20191029-x86_64-0-Hourly2-GP2'
    else:
        raise Exception('unknown distro ' + distro)

    kops_args = ""
    if networking:
        kops_args = kops_args + " --networking=" + networking

    kops_args = kops_args.strip()

    test_args = r'--ginkgo.skip=\[Slow\]|\[Serial\]|\[Disruptive\]|\[Flaky\]|\[Feature:.+\]|\[HPA\]|Dashboard|Services.*functioning.*NodePort' # pylint: disable=line-too-long

    suffix = ""
    if cloud:
        suffix += "-" + cloud
    if networking:
        suffix += "-" + networking
    if distro:
        suffix += "-" + distro

    tab = 'kops-grid' + suffix

    cron = build_cron(tab, on_hotlist=(tab in hotlist))

    y = template
    y = y.replace('{{tab}}', tab)
    y = y.replace('{{suffix}}', suffix)
    y = y.replace('{{kops_ssh_user}}', kops_ssh_user)
    y = y.replace('{{networking}}', networking)
    y = y.replace('{{kops_image}}', kops_image)
    y = y.replace('{{kops_args}}', kops_args)
    y = y.replace('{{test_args}}', test_args)
    y = y.replace('{{cron}}', cron)
    out = y

    spec = {
        'cloud': cloud,
        'networking': networking,
        'distro': distro,
    }
    jsonspec = json.dumps(spec)
    print("")
    print("# " + jsonspec)
    print(out.strip())

print("""# Test scenarios generated by build-grid.py (do not manually edit)
periodics:""")

build_test(cloud="aws", networking="flannel", distro="amazonlinux2")
build_test(cloud="aws", networking="flannel", distro="centos7")
build_test(cloud="aws", networking="flannel", distro="coreos")
build_test(cloud="aws", networking="flannel", distro="debian9")
build_test(cloud="aws", networking="flannel", distro="debian10")
build_test(cloud="aws", networking="flannel", distro="flatcar")
build_test(cloud="aws", networking="flannel", distro="rhel7")
build_test(cloud="aws", networking="flannel", distro="rhel8")
build_test(cloud="aws", networking="flannel", distro="ubuntu1604")
build_test(cloud="aws", networking="flannel", distro="ubuntu1804")
build_test(cloud="aws", networking="flannel", distro="ubuntu2004")
