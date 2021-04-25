#!/bin/bash

exec python bot.py &
exec hypercorn -b 0.0.0.0:${PORT} "server:app"