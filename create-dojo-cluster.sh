#!/bin/bash

set -e

ansible_script=${1:-site.yml}

[[ -z "${DOJO_SSH_PRIVATE_KEY_FILE}" ]] && read -rp "Path to OpenStack SSH private key file: " DOJO_SSH_PRIVATE_KEY_FILE
[[ -z "${DOJO_VAULT_PASSWORD_FILE}" ]] && read -rp "Path to Ansible vault password file: " DOJO_VAULT_PASSWORD_FILE
[[ -z "${DOJO_INVENTORY_FILE}" ]] && read -rp "Path to Ansible inventory file: " DOJO_INVENTORY_FILE

function createAnsiblePlaybookImage
{
    local checksum=$(find ansible -type f | sort | xargs cat | cksum | cut -d' ' -f1)
    local label="com.hpe.docker-hub.ansible-hash=${checksum}"

    if [[ -z "$(docker images --quiet --filter label=${label} ansible-playbook)" ]]
    then
      echo "Creating Ansible Playbook Docker image"
      pushd ansible
      docker build --tag ansible-playbook --label ${label} .
      popd
    fi
}

function absolutePath
{
    local path=$1
    [[ "${path}" =~ ^/.* ]] || path="$(pwd)/${path}"
    echo "${path}"
}

function runPlaybook
{
    local playbooks=$(absolutePath playbooks)
    local library=$(absolutePath library)
    local privateKey=$(absolutePath "${DOJO_SSH_PRIVATE_KEY_FILE}")
    local vault=$(absolutePath "${DOJO_VAULT_PASSWORD_FILE}")
    local inventory=$(absolutePath "${DOJO_INVENTORY_FILE}")
    local inventoryDirectory=$(dirname "${inventory}")
    local inventoryFile=$(basename "${inventory}")

    docker run --rm \
               --dns 16.110.135.51 \
               --volume "${playbooks}":/usr/src/playbooks:ro \
               --volume "${inventoryDirectory}":/usr/src/inventory:ro \
               --volume "${library}":/usr/src/library:ro \
               --volume "${privateKey}":/.ssh/private-key:ro \
               --volume "${vault}":/tmp/vault.txt:ro \
               --env ANSIBLE_FORCE_COLOR=true \
               ansible-playbook --verbose -vvv \
                                --private-key /.ssh/private-key \
                                --vault-password-file /tmp/vault.txt \
                                --module-path /usr/src/library \
                                --inventory "/usr/src/inventory/${inventoryFile}" \
                                $ansible_script
}

function main
{
    createAnsiblePlaybookImage
    runPlaybook
}

main
