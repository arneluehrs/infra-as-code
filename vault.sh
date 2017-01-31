#!/bin/bash

command=$1
vault=$2

function usage
{
    echo "Usage: $0 [encrypt|decrypt] path/to/vault" >&2 && exit 1
}

function vault
{
    [[ "${vault}" =~ ^/.* ]] || vault="$(pwd)/${vault}"
    vaultDirectory=$(dirname "${vault}")
    vaultFile=$(basename "${vault}")

    docker run --rm --interactive --tty \
               --volume "${vaultDirectory}":/usr/src/inventory \
               --entrypoint ansible-vault \
               ansible-playbook ${command} --ask-vault-pass "/usr/src/inventory/${vaultFile}"
}

[[ -z "${command}" || -z "${vault}" ]] && usage

case "${command}" in
  encrypt|decrypt) vault ;;
  *) usage ;;
esac
