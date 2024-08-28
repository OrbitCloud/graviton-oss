#!/bin/bash

cat <<EOF > ~/.bash_profile
. /home/oracle/scripts/setEnv.sh

alias dkprod=". ~/scripts/setEnv.sh dk"
alias seprod=". ~/scripts/setEnv.sh se"

bold=$(tput bold)
normal=$(tput sgr0)
echo "Commands: \${bold}dkprod\${normal} and \${bold}seprod\${normal} to switch environments"


alias cdo="cd \$ORACLE_HOME"
alias cdb="cd \$ORACLE_BASE"
alias cdh="cd \$ORACLE_BASE_HOME"

alias cdal="cd /opt/oracle/diag/rdbms/\${ORACLE_UNQNAME}/\${ORACLE_SID}/trace"

alias grenv="env | egrep "
EOF
