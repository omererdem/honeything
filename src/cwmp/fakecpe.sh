#!/bin/bash

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
CWMP="$DIR/cwmpd --platform=fakecpe --rcmd-port=0 --cpe-listener"
DELAY=2


$CWMP "$@"

code=$?
DNLD=download.tgz
if [ $code -eq 32 ] && [ -f $DNLD ]; then
  #tar xzf $DNLD
  #rm $DNLD
  echo "cwmpd exited deliberately.  Respawning in $DELAY seconds." >&2
  sleep $DELAY
  exec $DIR/fakecpe.sh "$@"
fi

exit 1
