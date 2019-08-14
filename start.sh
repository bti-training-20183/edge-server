 #!/bin/bash

echo 'Run cronjob'

mkdir /etc/cron.d
cp cron /etc/cron.d/cron
chmod 0644 /etc/cron.d/cron
crontab /etc/cron.d/cron
crond -b -d 8

echo 'Run server'

python server.py