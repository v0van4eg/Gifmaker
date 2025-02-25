#!/bin/bash

# Создаем структуру каталогов
mkdir -p roles/glusterfs/{defaults,files,handlers,meta,tasks,templates,vars}

# Заполняем файлы

cat << EOF > roles/glusterfs/defaults/main.yml
---
# Default variables for the role
glusterfs_version: "latest"
glusterfs_mount_point: "/mnt/datavol"
glusterfs_volume_name: "datavol"
glusterfs_bricks: ["/data/brick1", "/data/brick2"]
EOF

cat << EOF > roles/glusterfs/files/glusterfs.repo
[glusterfs]
name=GlusterFS Repository
baseurl=https://download.gluster.org/pub/gluster/glusterfs/LATEST/CentOS/glusterfs,epel,\$releasever,x86_64/
gpgcheck=0
enabled=1
EOF

cat << EOF > roles/glusterfs/handlers/main.yml
---
- name: Restart glusterd service
  systemd:
    name: glusterd
    state: restarted
    enabled: yes
EOF

cat << EOF > roles/glusterfs/meta/main.yml
---
dependencies: []
galaxy_info:
  author: your_name
  description: Install and configure GlusterFS
  company: Your Company
  license: MIT
  min_ansible_version: 2.9
  platforms:
    - name: EL
      versions:
        - all
  galaxy_tags:
    - storage
    - glusterfs
EOF

cat << EOF > roles/glusterfs/tasks/install_glusterfs.yml
---
- name: Add GlusterFS repository
  copy:
    src: glusterfs.repo
    dest: /etc/yum.repos.d/glusterfs.repo
  when: ansible_os_family == 'RedHat'

- name: Install GlusterFS packages
  package:
    name: glusterfs-server
    state: present

- name: Start and enable glusterd service
  systemd:
    name: glusterd
    state: started
    enabled: yes
EOF

cat << EOF > roles/glusterfs/tasks/create_volume.yml
---
- name: Create GlusterFS volume
  command: >
    gluster volume create {{ glusterfs_volume_name }} replica 3 {{ groups['workers'] | join(':/') }}{{ glusterfs_bricks[0] }}
  args:
    warn: false
  register: volume_create_result
  changed_when: "'Volume creation successful' in volume_create_result.stdout"

- name: Start GlusterFS volume
  command: gluster volume start {{ glusterfs_volume_name }}
  args:
    warn: false
  when: "'Volume creation successful' in volume_create_result.stdout"

- name: Mount GlusterFS volume
  mount:
    path: "{{ glusterfs_mount_point }}"
    src: "{{ item }}"
    fstype: glusterfs
    opts: defaults,_netdev
    state: mounted
  with_items:
    - "{{ groups['managers'][0] }}:{{ glusterfs_volume_name }}"
EOF

cat << EOF > roles/glusterfs/tasks/main.yml
---
- include_tasks: install_glusterfs.yml

- include_tasks: create_volume.yml
  when: inventory_hostname in groups['managers']
EOF

cat << EOF > roles/glusterfs/templates/glusterfs.conf.j2
{% for brick in glusterfs_bricks %}
{{ brick }}
{% endfor %}
EOF

cat << EOF > roles/glusterfs/vars/main.yml
---
# Variables for the role
glusterfs_peers: "{{ groups['workers'] }}"
EOF

echo "Структура каталогов и файлы успешно созданы."
