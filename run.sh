#!/bin/bash

exec python tmp/app/bot.py &
exec hypercorn -b 0.0.0.0:9000 "tmp/app/server:app"