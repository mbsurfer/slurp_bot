#!/bin/bash

exec python tmp/app/bot.py &
exec hypercorn -b 0.0.0.0:${PORT} "tmp/app/server:app"